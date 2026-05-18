"""Unit тесты для проверки схем."""

import pytest
from pydantic import ValidationError

from app.schemas import ClientEventCreate, ServiceCreate


def test_service_create_accepts_valid_http_url() -> None:
    payload = ServiceCreate(name="MIREA", url="https://www.mirea.ru")

    assert payload.name == "MIREA"
    assert str(payload.url).startswith("https://www.mirea.ru")


def test_service_create_rejects_empty_name() -> None:
    with pytest.raises(ValidationError):
        ServiceCreate(name="", url="https://example.com")


def test_service_create_rejects_url_without_http_scheme() -> None:
    with pytest.raises(ValidationError):
        ServiceCreate(name="Bad URL", url="ftp://example.com")


def test_service_create_rejects_url_with_spaces() -> None:
    with pytest.raises(ValidationError):
        ServiceCreate(name="Bad URL", url="https://example.com/test page")


def test_client_event_create_accepts_regular_payload() -> None:
    event = ClientEventCreate(
        service_id=1,
        event_type="page_load",
        payload={"load_time_ms": 240},
    )

    assert event.service_id == 1
    assert event.event_type == "page_load"
    assert event.payload["load_time_ms"] == 240


def test_client_event_create_rejects_password_in_payload() -> None:
    with pytest.raises(ValidationError):
        ClientEventCreate(
            service_id=1,
            event_type="js_error",
            payload={"password": "secret"},
        )


def test_client_event_create_rejects_email_in_payload() -> None:
    with pytest.raises(ValidationError):
        ClientEventCreate(
            service_id=1,
            event_type="client_error",
            payload={"email": "user@example.com"},
        )


def test_client_event_create_rejects_invalid_service_id() -> None:
    with pytest.raises(ValidationError):
        ClientEventCreate(
            service_id=0,
            event_type="page_load",
            payload={},
        )
