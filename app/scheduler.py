"""Background scheduler for periodic service checks."""

import logging
from threading import Event, Thread
from time import sleep

from app.database import SessionLocal
from app.models import Service
from app.services.checker import perform_service_check

logger = logging.getLogger(__name__)

INTERVAL_SECONDS = 60
_stop_event = Event()


def run_checks_once() -> None:
    """Run one check cycle for all active services."""
    db = SessionLocal()
    try:
        services = db.query(Service).filter(Service.is_active.is_(True)).all()
        for service in services:
            try:
                perform_service_check(db, service.id)
            except Exception:
                logger.exception("Service check failed for service_id=%s", service.id)
    finally:
        db.close()


def _scheduler_loop() -> None:
    while not _stop_event.is_set():
        run_checks_once()
        sleep(INTERVAL_SECONDS)


def start_scheduler() -> Thread:
    """Start background check thread."""
    thread = Thread(target=_scheduler_loop, daemon=True)
    thread.start()
    return thread
