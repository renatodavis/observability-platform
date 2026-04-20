import json
from typing import Any

import aio_pika

from app.config import get_settings


async def publish_event(queue: str, payload: dict[str, Any]) -> None:
    settings = get_settings()
    connection = await aio_pika.connect_robust(settings.rabbitmq_url)
    try:
        channel = await connection.channel()
        await channel.declare_queue(queue, durable=True)
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
