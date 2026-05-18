"""Unit тесты для хранения событий мониторинга на стороне клиента."""

from sqlalchemy.orm import Session

from app.models import ClientEvent
from app.schemas import ClientEventCreate


def test_client_event_payload_can_store_page_load_metric(db_session: Session, test_service) -> None:
    payload = ClientEventCreate(
        service_id=test_service.id,
        event_type="page_load",
        payload={"load_time_ms": 180},
    )

    event = ClientEvent(
        service_id=payload.service_id,
        event_type=payload.event_type,
        payload=payload.payload,
    )
    db_session.add(event)
    db_session.commit()
    db_session.refresh(event)

    assert event.id is not None
    assert event.event_type == "page_load"
    assert event.payload["load_time_ms"] == 180


def test_client_event_payload_can_store_js_error(db_session: Session, test_service) -> None:
    payload = ClientEventCreate(
        service_id=test_service.id,
        event_type="js_error",
        payload={"message": "TypeError", "source": "monitor.js"},
    )

    event = ClientEvent(
        service_id=payload.service_id,
        event_type=payload.event_type,
        payload=payload.payload,
    )
    db_session.add(event)
    db_session.commit()
    db_session.refresh(event)

    assert event.event_type == "js_error"
    assert event.payload["message"] == "TypeError"
    assert event.payload["source"] == "monitor.js"
