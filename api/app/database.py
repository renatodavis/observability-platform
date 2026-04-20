import os
from collections.abc import Iterator
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import get_settings


class Base(DeclarativeBase):
    pass


_settings = get_settings()

if _settings.api_database_url.startswith("sqlite:///"):
    db_path = _settings.api_database_url.replace("sqlite:///", "", 1)
    if db_path and not db_path.startswith(":memory:"):
        try:
            Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        except PermissionError:
            # Directory will be mounted by Docker; fall through and let SQLAlchemy
            # raise a clear error later if the path is still unusable at runtime.
            pass

engine = create_engine(
    _settings.api_database_url,
    connect_args={"check_same_thread": False}
    if _settings.api_database_url.startswith("sqlite")
    else {},
    future=True,
)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def init_db() -> None:
    # Import models so they register on Base.metadata
    from app import models  # noqa: F401

    Base.metadata.create_all(bind=engine)


def get_db() -> Iterator[Session]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def db_path_exists() -> bool:
    if _settings.api_database_url.startswith("sqlite:///"):
        db_path = _settings.api_database_url.replace("sqlite:///", "", 1)
        return os.path.exists(db_path) if db_path else False
    return True
