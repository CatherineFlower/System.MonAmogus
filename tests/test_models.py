"""Unit тесты для объектов ORM, хранящих данные мониторинга."""

from sqlalchemy.orm import Session

from app.models import ClientEvent, ServerCheck, Service


def test_service_can_store_basic_monitoring_target(db_session: Session) -> None:
    service = Service(
        name="Kinopoisk",
        url="https://www.kinopoisk.ru",
        description="Monitoring target",
        is_active=True,
        sort_order=10,
    )

    db_session.add(service)
    db_session.commit()
    db_session.refresh(service)

    assert service.id is not None
    assert service.name == "Kinopoisk"
    assert service.is_active is True
    assert service.sort_order == 10


def test_server_check_is_linked_to_service(db_session: Session, test_service: Service) -> None:
    check = ServerCheck(
        service_id=test_service.id,
        status_code=200,
        response_time_ms=150,
        is_available=True,
        error_text=None,
    )

    db_session.add(check)
    db_session.commit()
    db_session.refresh(check)

    assert check.service_id == test_service.id
    assert check.service.id == test_service.id
    assert test_service.checks[0].id == check.id


def test_client_event_is_linked_to_service(db_session: Session, test_service: Service) -> None:
    event = ClientEvent(
        service_id=test_service.id,
        event_type="js_error",
        payload={"message": "ReferenceError"},
    )

    db_session.add(event)
    db_session.commit()
    db_session.refresh(event)

    assert event.service_id == test_service.id
    assert event.service.id == test_service.id
    assert test_service.client_events[0].id == event.id


def test_deleting_service_removes_related_checks_and_events(db_session: Session, test_service: Service) -> None:
    check = ServerCheck(
        service_id=test_service.id,
        status_code=503,
        response_time_ms=300,
        is_available=False,
        error_text="Service unavailable",
    )
    event = ClientEvent(
        service_id=test_service.id,
        event_type="offline",
        payload={"online": False},
    )

    db_session.add_all([check, event])
    db_session.commit()

    service_id = test_service.id
    db_session.delete(test_service)
    db_session.commit()

    assert db_session.query(Service).filter(Service.id == service_id).first() is None
    assert db_session.query(ServerCheck).filter(ServerCheck.service_id == service_id).all() == []
    assert db_session.query(ClientEvent).filter(ClientEvent.service_id == service_id).all() == []
