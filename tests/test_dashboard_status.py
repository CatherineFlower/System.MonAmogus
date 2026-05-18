"""Unit тесты для расчета статуса сервиса.

Эти тесты охватывают основной объект исследования: мониторинг стабильности ИТ-сервисов.
Они проверяют, как система интерпретирует проверки сервера и события на стороне клиента.
"""

from types import SimpleNamespace

from app.services.dashboard import (
    STATUS_AVAILABLE,
    STATUS_CLIENT_ISSUES,
    STATUS_UNAVAILABLE,
    calculate_service_status,
    has_client_errors,
)


def test_status_unavailable_when_no_check() -> None:
    result = calculate_service_status(last_check=None, recent_events=[])

    assert result == STATUS_UNAVAILABLE


def test_status_unavailable_when_last_check_failed() -> None:
    last_check = SimpleNamespace(is_available=False, error_text="Connection timeout")

    result = calculate_service_status(last_check=last_check, recent_events=[])

    assert result == STATUS_UNAVAILABLE


def test_status_unavailable_when_check_has_error_text() -> None:
    last_check = SimpleNamespace(is_available=True, error_text="HTTP error")

    result = calculate_service_status(last_check=last_check, recent_events=[])

    assert result == STATUS_UNAVAILABLE


def test_status_client_issues_when_service_available_but_js_error_exists() -> None:
    last_check = SimpleNamespace(is_available=True, error_text=None)
    events = [SimpleNamespace(event_type="js_error", payload={"message": "Uncaught TypeError"})]

    result = calculate_service_status(last_check=last_check, recent_events=events)

    assert result == STATUS_CLIENT_ISSUES


def test_status_client_issues_when_service_available_but_promise_error_exists() -> None:
    last_check = SimpleNamespace(is_available=True, error_text=None)
    events = [SimpleNamespace(event_type="promise_error", payload={"reason": "Rejected promise"})]

    result = calculate_service_status(last_check=last_check, recent_events=events)

    assert result == STATUS_CLIENT_ISSUES


def test_status_client_issues_when_service_available_but_offline_event_exists() -> None:
    last_check = SimpleNamespace(is_available=True, error_text=None)
    events = [SimpleNamespace(event_type="offline", payload={"online": False})]

    result = calculate_service_status(last_check=last_check, recent_events=events)

    assert result == STATUS_CLIENT_ISSUES


def test_status_available_when_check_ok_and_no_client_errors() -> None:
    last_check = SimpleNamespace(is_available=True, error_text=None)
    events = [SimpleNamespace(event_type="page_load", payload={"load_time_ms": 120})]

    result = calculate_service_status(last_check=last_check, recent_events=events)

    assert result == STATUS_AVAILABLE


def test_has_client_errors_detects_error_text_in_payload() -> None:
    events = [{"event_type": "page_load", "payload": {"error_text": "Frontend error"}}]

    assert has_client_errors(events) is True


def test_has_client_errors_returns_false_for_regular_page_load() -> None:
    events = [{"event_type": "page_load", "payload": {"load_time_ms": 150}}]

    assert has_client_errors(events) is False
