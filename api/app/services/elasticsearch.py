from typing import Any

from elasticsearch import AsyncElasticsearch

from app.config import get_settings

_client: AsyncElasticsearch | None = None


def get_es_client() -> AsyncElasticsearch:
    global _client
    if _client is None:
        settings = get_settings()
        kwargs: dict[str, Any] = {"hosts": [settings.elasticsearch_url]}
        if settings.elasticsearch_user and settings.elasticsearch_password:
            kwargs["basic_auth"] = (
                settings.elasticsearch_user,
                settings.elasticsearch_password,
            )
        _client = AsyncElasticsearch(**kwargs)
    return _client


async def close_es_client() -> None:
    global _client
    if _client is not None:
        await _client.close()
        _client = None
