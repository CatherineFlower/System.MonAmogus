"""Unit тесты для проверки HTTP-сервисов."""

import httpx
from sqlalchemy.orm import Session

from app.models import ServerCheck
from app.services import checker


class FakeResponse:
    def __init__(self, status_code: int) -> None:
        self.status_code = status_code


def test_perform_service_check_saves_available_result(monkeypatch, db_session: Session, test_service) -> None:
    def fake_get(url: str, timeout: int, follow_redirects: bool) -> FakeResponse:
        assert url == test_service.url
        assert timeout == checker.TIMEOUT_SECONDS
        assert follow_redirects is True
        return FakeResponse(status_code=200)

    monkeypatch.setattr(checker.httpx, "get", fake_get)

    check = checker.perform_service_check(db_session, test_service.id)

    assert check.service_id == test_service.id
    assert check.status_code == 200
    assert check.is_available is True
    assert check.error_text is None
    assert check.response_time_ms >= 0

    saved_check = db_session.query(ServerCheck).filter(ServerCheck.id == check.id).first()
    assert saved_check is not None
    assert saved_check.is_available is True


def test_perform_service_check_saves_unavailable_result_for_500(monkeypatch, db_session: Session, test_service) -> None:
    def fake_get(url: str, timeout: int, follow_redirects: bool) -> FakeResponse:
        return FakeResponse(status_code=500)

    monkeypatch.setattr(checker.httpx, "get", fake_get)

    check = checker.perform_service_check(db_session, test_service.id)

    assert check.status_code == 500
    assert check.is_available is False
    assert check.error_text is None


def test_perform_service_check_saves_error_text_on_timeout(monkeypatch, db_session: Session, test_service) -> None:
    def fake_get(url: str, timeout: int, follow_redirects: bool) -> FakeResponse:
        raise httpx.TimeoutException("timeout")

    monkeypatch.setattr(checker.httpx, "get", fake_get)

    check = checker.perform_service_check(db_session, test_service.id)

    assert check.status_code is None
    assert check.is_available is False
    assert check.error_text is not None
    assert "timeout" in check.error_text.lower()


def test_perform_service_check_raises_key_error_for_unknown_service(db_session: Session) -> None:
    try:
        checker.perform_service_check(db_session, service_id=9999)
    except KeyError as exc:
        assert "Service 9999 not found" in str(exc)
    else:
        raise AssertionError("KeyError was not raised")
