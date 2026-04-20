from typing import Any

from elasticsearch import NotFoundError
from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Integration as IntegrationModel
from app.schemas import Stats, StatsByIntegration
from app.services.elasticsearch import get_es_client

router = APIRouter(prefix="/stats", tags=["stats"])


@router.get("", response_model=Stats)
async def stats(db: Session = Depends(get_db)) -> Stats:
    es = get_es_client()
    integrations = db.execute(select(IntegrationModel)).scalars().all()
    indices = [i.index for i in integrations]
    if not indices:
        return Stats(total_events=0, by_integration=[], by_level=[])

    try:
        resp: dict[str, Any] = await es.search(
            index=",".join(indices),
            size=0,
            aggs={
                "by_integration": {
                    "terms": {"field": "integration.keyword", "size": 50}
                },
                "by_level": {"terms": {"field": "level.keyword", "size": 10}},
            },
            ignore_unavailable=True,
            allow_no_indices=True,
        )
    except NotFoundError:
        return Stats(total_events=0, by_integration=[], by_level=[])

    hits = resp.get("hits", {})
    total = hits.get("total", {}).get("value", 0) if isinstance(hits.get("total"), dict) else 0
    aggs = resp.get("aggregations", {}) or {}

    def to_buckets(key: str) -> list[StatsByIntegration]:
        items = aggs.get(key, {}).get("buckets", []) or []
        return [
            StatsByIntegration(integration=b.get("key", ""), count=b.get("doc_count", 0))
            for b in items
        ]

    return Stats(
        total_events=total,
        by_integration=to_buckets("by_integration"),
        by_level=to_buckets("by_level"),
    )
