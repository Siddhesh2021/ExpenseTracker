import os

os.environ.setdefault("APP_ENV", "test")
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ["WHATSAPP_VERIFY_TOKEN"] = "test-verify-token"
os.environ["WHATSAPP_ACCESS_TOKEN"] = "test-access-token"
os.environ["WHATSAPP_PHONE_NUMBER_ID"] = "test-phone-id"
os.environ["WHATSAPP_API_VERSION"] = "v21.0"

from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.db import models  # noqa: F401
from app.db.database import Base, get_engine, get_session_factory, reset_engine


@pytest.fixture(autouse=True)
def _reset_settings() -> Generator[None, None, None]:
    get_settings.cache_clear()
    reset_engine()
    yield
    reset_engine()
    get_settings.cache_clear()


@pytest.fixture
def client() -> Generator[TestClient, None, None]:
    from app.main import create_app

    engine = get_engine()
    Base.metadata.create_all(engine)
    with TestClient(create_app()) as test_client:
        yield test_client


@pytest.fixture
def db_session() -> Generator:
    engine = get_engine()
    Base.metadata.create_all(engine)
    session = get_session_factory()()
    try:
        yield session
    finally:
        session.close()
