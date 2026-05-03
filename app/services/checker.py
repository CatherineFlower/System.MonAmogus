"""Service URL availability checks via HTTP."""

from time import perf_counter

import httpx
from sqlalchemy.orm import Session

from app.models import ServerCheck, Service


TIMEOUT_SECONDS = 5


def perform_service_check(db: Session, service_id: int) -> ServerCheck:
    """Check the service URL and persist check result to DB."""
    service = db.query(Service).filter(Service.id == service_id).first()
    if service is None:
        raise KeyError(f"Service {service_id} not found")

    status_code: int | None = None
    response_time_ms = 0
    is_available = False
    error_text: str | None = None

    started = perf_counter()
    try:
        response = httpx.get(service.url, timeout=TIMEOUT_SECONDS, follow_redirects=True)
        response_time_ms = int((perf_counter() - started) * 1000)
        status_code = response.status_code
        is_available = 200 <= response.status_code < 400
    except httpx.HTTPError as exc:
        response_time_ms = int((perf_counter() - started) * 1000)
        error_text = str(exc)

    check = ServerCheck(
        service_id=service_id,
        status_code=status_code,
        response_time_ms=response_time_ms,
        is_available=is_available,
        error_text=error_text,
    )
    db.add(check)
    db.commit()
    db.refresh(check)
    return check
