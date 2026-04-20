from datetime import UTC, datetime
from typing import Any

from elasticsearch import NotFoundError
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Integration as IntegrationModel
from app.schemas import EventHit, EventPublish, EventPublishResponse, EventsPage
from app.services.elasticsearch import get_es_client
from app.services.rabbitmq import publish_event

router = APIRouter(prefix="/events", tags=["events"])


@router.post("/publish", response_model=EventPublishResponse)
async def publish(payload: EventPublish, db: Session = Depends(get_db)) -> EventPublishResponse:
    integration = db.execute(
        select(IntegrationModel).where(IntegrationModel.name == payload.integration)
    ).scalar_one_or_none()
    if integration is None:
        raise HTTPException(
            status_code=404,
            detail=f"integration '{payload.integration}' not found — create it first",
        )
    if not integration.enabled:
        raise HTTPException(status_code=409, detail="integration is disabled")

    body = {
        "@timestamp": datetime.now(UTC).isoformat(),
        "integration": integration.name,
        "level": payload.level,
        "message": payload.message,
        "source": payload.source or "api",
        "attributes": payload.attributes,
    }
    await publish_event(integration.queue, body)
    return EventPublishResponse(status="queued", queue=integration.queue)


@router.get("", response_model=EventsPage)
async def search_events(
    integration: str | None = Query(default=None),
    level: str | None = Query(default=None),
    q: str | None = Query(default=None, description="full-text query over message field"),
    size: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
) -> EventsPage:
    es = get_es_client()

    # Determine which index(es) to search over. If integration is provided we scope to it;
    # otherwise we query all configured integrations.
    if integration:
        integ = db.execute(
            select(IntegrationModel).where(IntegrationModel.name == integration)
        ).scalar_one_or_none()
        if integ is None:
            raise HTTPException(status_code=404, detail="integration not found")
        indices = [integ.index]
    else:
        integrations = db.execute(select(IntegrationModel)).scalars().all()
        indices = [i.index for i in integrations] or ["*-logs"]

    must: list[dict[str, Any]] = []
    if level:
        must.append({"term": {"level.keyword": level}})
    if q:
        must.append({"match": {"message": q}})
    query: dict[str, Any] = {"bool": {"must": must}} if must else {"match_all": {}}

    try:
        resp = await es.search(
            index=",".join(indices),
            query=query,
            sort=[{"@timestamp": {"order": "desc"}}],
            size=size,
            from_=offset,
            ignore_unavailable=True,
            allow_no_indices=True,
        )
    except NotFoundError:
        return EventsPage(total=0, items=[])

    hits = resp.get("hits", {})
    total = hits.get("total", {}).get("value", 0) if isinstance(hits.get("total"), dict) else 0
    items: list[EventHit] = []
    for hit in hits.get("hits", []):
        src = hit.get("_source", {}) or {}
        items.append(
            EventHit(
                id=hit.get("_id", ""),
                index=hit.get("_index", ""),
                timestamp=src.get("@timestamp"),
                level=src.get("level"),
                message=src.get("message"),
                integration=src.get("integration"),
                source=src,
            )
        )
    return EventsPage(total=total, items=items)
