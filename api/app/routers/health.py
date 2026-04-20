from fastapi import APIRouter

from app.schemas import Health
from app.services.elasticsearch import get_es_client
from app.services.rabbitmq import ping as rabbit_ping

router = APIRouter(tags=["health"])


@router.get("/health", response_model=Health)
async def health() -> Health:
    es = get_es_client()
    try:
        es_ok = await es.ping()
    except Exception:
        es_ok = False
    rabbit_ok = await rabbit_ping()
    status = "ok" if es_ok and rabbit_ok else "degraded"
    return Health(status=status, elasticsearch=es_ok, rabbitmq=rabbit_ok)
