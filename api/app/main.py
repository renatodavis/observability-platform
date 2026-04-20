from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.database import init_db
from app.logging_config import configure_logging
from app.routers import events, health, integrations, stats
from app.services.elasticsearch import close_es_client


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    configure_logging(settings.api_log_level)
    logger = structlog.get_logger()
    init_db()
    logger.info("api.startup", rabbitmq=settings.rabbitmq_host, es=settings.elasticsearch_url)
    yield
    await close_es_client()
    logger.info("api.shutdown")


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="Observability Platform API",
        version="0.1.0",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        lifespan=lifespan,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(health.router, prefix="/api")
    app.include_router(integrations.router, prefix="/api")
    app.include_router(events.router, prefix="/api")
    app.include_router(stats.router, prefix="/api")
    return app


app = create_app()
