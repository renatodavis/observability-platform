"""RabbitMQ -> Elasticsearch consumer worker.

Polls the API for configured integrations and spawns a consumer for each one. New
integrations are picked up automatically at the next poll tick. Messages that fail to
index after `WORKER_MAX_RETRIES` attempts are routed to a dead-letter queue.
"""
from __future__ import annotations

import asyncio
import json
import logging
import signal
import sys
from dataclasses import dataclass
from typing import Any

import aio_pika
import httpx
import structlog
from aio_pika.abc import AbstractIncomingMessage
from elasticsearch import AsyncElasticsearch
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    rabbitmq_host: str = Field(default="rabbitmq", alias="RABBITMQ_HOST")
    rabbitmq_port: int = Field(default=5672, alias="RABBITMQ_PORT")
    rabbitmq_user: str = Field(default="observ", alias="RABBITMQ_USER")
    rabbitmq_pass: str = Field(default="observ", alias="RABBITMQ_PASS")
    rabbitmq_vhost: str = Field(default="/", alias="RABBITMQ_VHOST")
    elasticsearch_url: str = Field(
        default="http://elasticsearch:9200", alias="ELASTICSEARCH_URL"
    )
    api_url: str = Field(default="http://api:8000", alias="API_URL")
    prefetch: int = Field(default=32, alias="WORKER_PREFETCH")
    poll_interval: int = Field(default=10, alias="WORKER_POLL_INTERVAL_SECONDS")
    max_retries: int = Field(default=3, alias="WORKER_MAX_RETRIES")
    log_level: str = Field(default="INFO", alias="WORKER_LOG_LEVEL")

    @property
    def rabbitmq_url(self) -> str:
        vhost = self.rabbitmq_vhost
        if not vhost.startswith("/"):
            vhost = f"/{vhost}"
        return (
            f"amqp://{self.rabbitmq_user}:{self.rabbitmq_pass}"
            f"@{self.rabbitmq_host}:{self.rabbitmq_port}{vhost}"
        )


@dataclass
class Integration:
    id: int
    name: str
    queue: str
    index: str
    enabled: bool


def configure_logging(level: str) -> None:
    logging.basicConfig(stream=sys.stdout, level=level.upper(), format="%(message)s")
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(
            getattr(logging, level.upper(), logging.INFO)
        ),
        cache_logger_on_first_use=True,
    )


log = structlog.get_logger()


class IntegrationConsumer:
    """Owns one RabbitMQ consumer + the lifecycle of its queue/DLQ."""

    def __init__(
        self,
        settings: Settings,
        integration: Integration,
        channel: aio_pika.abc.AbstractChannel,
        es: AsyncElasticsearch,
    ) -> None:
        self.settings = settings
        self.integration = integration
        self.channel = channel
        self.es = es
        self._consumer_tag: str | None = None
        self._queue: aio_pika.abc.AbstractQueue | None = None

    @property
    def dlq_name(self) -> str:
        return f"{self.integration.queue}.dlq"

    async def start(self) -> None:
        dlx_exchange = await self.channel.declare_exchange(
            f"{self.integration.queue}.dlx", aio_pika.ExchangeType.DIRECT, durable=True
        )
        dlq = await self.channel.declare_queue(self.dlq_name, durable=True)
        await dlq.bind(dlx_exchange, routing_key=self.integration.queue)

        queue = await self.channel.declare_queue(
            self.integration.queue,
            durable=True,
            arguments={
                "x-dead-letter-exchange": dlx_exchange.name,
                "x-dead-letter-routing-key": self.integration.queue,
            },
        )
        self._queue = queue
        self._consumer_tag = await queue.consume(self._on_message)
        log.info(
            "worker.consumer.started",
            integration=self.integration.name,
            queue=self.integration.queue,
            index=self.integration.index,
        )

    async def stop(self) -> None:
        if self._queue and self._consumer_tag:
            await self._queue.cancel(self._consumer_tag)
            log.info("worker.consumer.stopped", integration=self.integration.name)

    async def _on_message(self, message: AbstractIncomingMessage) -> None:
        headers = dict(message.headers or {})
        attempt = int(headers.get("x-attempt", 0)) + 1
        try:
            payload: dict[str, Any] = json.loads(message.body.decode("utf-8"))
        except Exception as exc:  # malformed body -> DLQ
            log.warning(
                "worker.message.invalid",
                integration=self.integration.name,
                error=str(exc),
            )
            await message.reject(requeue=False)
            return

        try:
            await self.es.index(index=self.integration.index, document=payload)
            await message.ack()
        except Exception as exc:
            if attempt >= self.settings.max_retries:
                log.error(
                    "worker.message.dead_lettered",
                    integration=self.integration.name,
                    attempts=attempt,
                    error=str(exc),
                )
                await message.reject(requeue=False)
                return

            log.warning(
                "worker.message.retry",
                integration=self.integration.name,
                attempt=attempt,
                error=str(exc),
            )
            # Republish with incremented attempt counter and delay
            await asyncio.sleep(min(2**attempt, 10))
            await self.channel.default_exchange.publish(
                aio_pika.Message(
                    body=message.body,
                    content_type=message.content_type,
                    delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
                    headers={**headers, "x-attempt": attempt},
                ),
                routing_key=self.integration.queue,
            )
            await message.ack()


class WorkerOrchestrator:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.consumers: dict[int, IntegrationConsumer] = {}
        self._stop_event = asyncio.Event()

    def stop(self) -> None:
        self._stop_event.set()

    async def fetch_integrations(self, client: httpx.AsyncClient) -> list[Integration]:
        resp = await client.get(f"{self.settings.api_url}/api/integrations", timeout=5)
        resp.raise_for_status()
        return [
            Integration(
                id=it["id"],
                name=it["name"],
                queue=it["queue"],
                index=it["index"],
                enabled=it["enabled"],
            )
            for it in resp.json()
        ]

    async def run(self) -> None:
        log.info(
            "worker.starting",
            api=self.settings.api_url,
            rabbitmq=self.settings.rabbitmq_host,
            es=self.settings.elasticsearch_url,
        )
        connection = await aio_pika.connect_robust(self.settings.rabbitmq_url)
        channel = await connection.channel()
        await channel.set_qos(prefetch_count=self.settings.prefetch)
        es = AsyncElasticsearch(hosts=[self.settings.elasticsearch_url])

        try:
            async with httpx.AsyncClient() as client:
                while not self._stop_event.is_set():
                    try:
                        integrations = await self.fetch_integrations(client)
                    except Exception as exc:
                        log.warning("worker.api.unreachable", error=str(exc))
                        await self._sleep_or_stop(self.settings.poll_interval)
                        continue

                    desired = {i.id: i for i in integrations if i.enabled}

                    # Start new / changed consumers
                    for ident, integ in desired.items():
                        existing = self.consumers.get(ident)
                        if existing is None:
                            consumer = IntegrationConsumer(
                                self.settings, integ, channel, es
                            )
                            try:
                                await consumer.start()
                                self.consumers[ident] = consumer
                            except Exception as exc:
                                log.error(
                                    "worker.consumer.start_failed",
                                    integration=integ.name,
                                    error=str(exc),
                                )
                        elif (
                            existing.integration.queue != integ.queue
                            or existing.integration.index != integ.index
                        ):
                            await existing.stop()
                            consumer = IntegrationConsumer(
                                self.settings, integ, channel, es
                            )
                            await consumer.start()
                            self.consumers[ident] = consumer

                    # Stop consumers removed/disabled
                    for ident in list(self.consumers.keys()):
                        if ident not in desired:
                            await self.consumers[ident].stop()
                            del self.consumers[ident]

                    await self._sleep_or_stop(self.settings.poll_interval)
        finally:
            for consumer in list(self.consumers.values()):
                try:
                    await consumer.stop()
                except Exception:
                    pass
            await es.close()
            await connection.close()
            log.info("worker.stopped")

    async def _sleep_or_stop(self, seconds: int) -> None:
        try:
            await asyncio.wait_for(self._stop_event.wait(), timeout=seconds)
        except asyncio.TimeoutError:
            return


async def main() -> None:
    settings = Settings()
    configure_logging(settings.log_level)
    orchestrator = WorkerOrchestrator(settings)

    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, orchestrator.stop)

    await orchestrator.run()


if __name__ == "__main__":
    asyncio.run(main())
