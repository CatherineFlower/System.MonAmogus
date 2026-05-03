"""Pydantic schemas for API request/response validation."""

from datetime import datetime
from urllib.parse import urlparse

from pydantic import BaseModel, Field, HttpUrl, field_validator



FORBIDDEN_PII_KEYS = {"password", "passwd", "token", "secret", "ssn", "passport", "credit_card", "card_number", "email", "phone"}

class ServiceCreate(BaseModel):
    """Payload for creating a monitored service."""

    name: str = Field(min_length=1, max_length=255)
    url: HttpUrl

    @field_validator("url", mode="before")
    @classmethod
    def validate_url_strict(cls, value: str) -> str:
        if value is None:
            raise ValueError("URL не должен быть пустым")
        raw = str(value).strip()
        if not raw:
            raise ValueError("URL не должен быть пустым")
        if len(raw) > 2048:
            raise ValueError("URL слишком длинный")
        if any(ch in raw for ch in ("\n", "\r", "\t", " ")):
            raise ValueError("URL содержит недопустимые символы")
        parsed = urlparse(raw)
        if parsed.scheme not in {"http", "https"}:
            raise ValueError("URL должен начинаться с http:// или https://")
        if not parsed.netloc:
            raise ValueError("URL должен содержать домен")
        return raw


class ServiceOut(BaseModel):
    """Service representation returned by API."""

    id: int
    name: str
    url: HttpUrl
    created_at: datetime
    last_check_status: str | None = None
    last_check_http_code: int | None = None
    last_check_latency_ms: int | None = None
    last_check_at: datetime | None = None
    check_source: str | None = None


class CheckOut(BaseModel):
    """Service check representation returned by API."""

    id: int
    service_id: int
    status_code: int | None
    response_time_ms: int
    is_available: bool
    error_text: str | None
    created_at: datetime


class ClientEventCreate(BaseModel):
    """Payload for creating a client-side event."""

    service_id: int = Field(gt=0)
    event_type: str = Field(min_length=1, max_length=120)
    payload: dict = Field(default_factory=dict)

    @field_validator("payload")
    @classmethod
    def validate_no_forbidden_pii(cls, value: dict) -> dict:
        """Reject payloads that contain prohibited personal data keys (NF-06)."""
        lowered = {str(key).lower() for key in value}
        forbidden = sorted(lowered.intersection(FORBIDDEN_PII_KEYS))
        if forbidden:
            raise ValueError(
                "Payload contains forbidden personal data fields: " + ", ".join(forbidden)
            )
        return value


class ClientEventOut(BaseModel):
    """Client event representation returned by API."""

    id: int
    service_id: int
    event_type: str
    payload: dict
    created_at: datetime


class ServiceDashboard(BaseModel):
    """Aggregated service metrics for dashboard endpoint."""

    service_id: int
    current_status: str
    total_checks: int
    ok_checks: int
    fail_checks: int
    uptime_percent: float
    avg_response_time_ms: float
    total_events: int
    recent_checks: list[CheckOut]
    recent_events: list[ClientEventOut]
