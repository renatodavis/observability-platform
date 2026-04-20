from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    api_host: str = Field(default="0.0.0.0", alias="API_HOST")
    api_port: int = Field(default=8000, alias="API_PORT")
    api_log_level: str = Field(default="INFO", alias="API_LOG_LEVEL")
    api_database_url: str = Field(
        default="sqlite:////data/app.db", alias="API_DATABASE_URL"
    )
    api_cors_origins: str = Field(
        default="http://localhost:5173", alias="API_CORS_ORIGINS"
    )

    rabbitmq_host: str = Field(default="rabbitmq", alias="RABBITMQ_HOST")
    rabbitmq_port: int = Field(default=5672, alias="RABBITMQ_PORT")
    rabbitmq_user: str = Field(default="observ", alias="RABBITMQ_USER")
    rabbitmq_pass: str = Field(default="observ", alias="RABBITMQ_PASS")
    rabbitmq_vhost: str = Field(default="/", alias="RABBITMQ_VHOST")

    elasticsearch_url: str = Field(
        default="http://elasticsearch:9200", alias="ELASTICSEARCH_URL"
    )
    elasticsearch_user: str = Field(default="", alias="ELASTICSEARCH_USER")
    elasticsearch_password: str = Field(default="", alias="ELASTICSEARCH_PASSWORD")

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.api_cors_origins.split(",") if o.strip()]

    @property
    def rabbitmq_url(self) -> str:
        return (
            f"amqp://{self.rabbitmq_user}:{self.rabbitmq_pass}"
            f"@{self.rabbitmq_host}:{self.rabbitmq_port}{self.rabbitmq_vhost}"
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()
