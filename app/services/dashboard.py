"""Dashboard aggregation and service status calculation helpers."""

from __future__ import annotations

from collections.abc import Sequence


STATUS_AVAILABLE = "Доступен"
STATUS_UNAVAILABLE = "Недоступен"
STATUS_CLIENT_ISSUES = "Проблемы у пользователей"

CLIENT_ERROR_TYPES = {"js_error", "promise_error", "offline", "client_error"}


def _get_attr(item: object, key: str, default=None):
    if isinstance(item, dict):
        return item.get(key, default)
    return getattr(item, key, default)


def has_client_errors(events: Sequence[object]) -> bool:
    """Return True when any client event indicates user-side problems."""
    for event in events:
        if _get_attr(event, "event_type") in CLIENT_ERROR_TYPES:
            return True
        payload = _get_attr(event, "payload", {}) or {}
        if payload.get("error_text"):
            return True
    return False


def calculate_service_status(last_check: object | None, recent_events: Sequence[object]) -> str:
    """Calculate current service status from latest check and client events."""
    if not last_check:
        return STATUS_UNAVAILABLE

    if not _get_attr(last_check, "is_available") or _get_attr(last_check, "error_text"):
        return STATUS_UNAVAILABLE

    if has_client_errors(recent_events):
        return STATUS_CLIENT_ISSUES

    return STATUS_AVAILABLE
