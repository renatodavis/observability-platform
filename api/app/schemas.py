from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class IntegrationBase(BaseModel):
    name: str = Field(min_length=1, max_length=128)
    description: str = ""
    queue: str = Field(min_length=1, max_length=256)
    index: str = Field(min_length=1, max_length=256)
    enabled: bool = True


class IntegrationCreate(IntegrationBase):
    pass


class IntegrationUpdate(BaseModel):
    description: str | None = None
    queue: str | None = None
    index: str | None = None
    enabled: bool | None = None


class Integration(IntegrationBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
    updated_at: datetime


class EventPublish(BaseModel):
    integration: str = Field(min_length=1, max_length=128)
    level: str = Field(default="info")
    message: str = Field(min_length=1)
    source: str | None = None
    attributes: dict[str, Any] = Field(default_factory=dict)


class EventPublishResponse(BaseModel):
    status: str
    queue: str


class EventHit(BaseModel):
    id: str
    index: str
    timestamp: str | None = None
    level: str | None = None
    message: str | None = None
    integration: str | None = None
    source: dict[str, Any]


class EventsPage(BaseModel):
    total: int
    items: list[EventHit]


class StatsByIntegration(BaseModel):
    integration: str
    count: int


class Stats(BaseModel):
    total_events: int
    by_integration: list[StatsByIntegration]
    by_level: list[StatsByIntegration]


class Health(BaseModel):
    status: str
    elasticsearch: bool
    rabbitmq: bool
