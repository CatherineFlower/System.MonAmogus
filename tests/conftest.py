"""Тестовые приложения для Unit тестов MonAmogus.

В тестах используется изолированная база данных SQLite, хранящаяся в памяти. Это позволяет проверять
логику предметной области приложения, не обращаясь к реальной базе данных PostgreSQL.
"""

from collections.abc import Generator

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.database import Base
from app.models import Service


@pytest.fixture()
def db_session() -> Generator[Session, None, None]:
    """Create isolated database session for each unit test."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
    )

    TestingSessionLocal = sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=engine,
    )

    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()

    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture()
def test_service(db_session: Session) -> Service:
    """Create one monitored service for tests."""
    service = Service(
        name="Test Service",
        url="https://example.com",
        description="Unit-test service",
        is_active=True,
        sort_order=0,
    )

    db_session.add(service)
    db_session.commit()
    db_session.refresh(service)

    return service
