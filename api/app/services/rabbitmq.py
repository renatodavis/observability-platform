import json
from typing import Any

import aio_pika
from aio_pika.abc import AbstractChannel

from app.config import get_settings


async def declare_topology(
    channel: AbstractChannel, queue: str
) -> aio_pika.abc.AbstractQueue:
    """Declare the queue together with its DLX/DLQ topology.

    Must stay in sync with the worker's declaration (see `worker/worker.py`) so that
    API and worker present identical `arguments` to RabbitMQ; otherwise the broker
    rejects the second declaration with PRECONDITION_FAILED.
    """
    dlx_name = f"{queue}.dlx"
    dlx = await channel.declare_exchange(dlx_name, aio_pika.ExchangeType.DIRECT, durable=True)
    dlq = await channel.declare_queue(f"{queue}.dlq", durable=True)
    await dlq.bind(dlx, routing_key=queue)
    return await channel.declare_queue(
        queue,
        durable=True,
        arguments={
            "x-dead-letter-exchange": dlx_name,
            "x-dead-letter-routing-key": queue,
        },
    )


async def publish_event(queue: str, payload: dict[str, Any]) -> None:
    settings = get_settings()
    connection = await aio_pika.connect_robust(settings.rabbitmq_url)
    try:
        channel = await connection.channel()
        await declare_topology(channel, queue)
        await channel.default_exchange.publish(
            aio_pika.Message(
                body=json.dumps(payload).encode("utf-8"),
                content_type="application/json",
                delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
            ),
            routing_key=queue,
        )
    finally:
        await connection.close()


async def ping() -> bool:
    settings = get_settings()
    try:
        connection = await aio_pika.connect_robust(settings.rabbitmq_url, timeout=3)
        await connection.close()
        return True
    except Exception:
        return False
