"""Service checks API endpoints."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import ClientEvent, ServerCheck, Service
from app.schemas import CheckOut, ClientEventOut, ServiceDashboard
from app.services.dashboard import calculate_service_status

router = APIRouter(prefix="/api/services", tags=["checks"])

RECENT_ITEMS_LIMIT = 10


@router.post("/{id}/check", response_model=CheckOut, status_code=201)
def create_service_check(id: int, db: Session = Depends(get_db)) -> CheckOut:
    service = db.query(Service).filter(Service.id == id).first()
    if not service:
        raise HTTPException(status_code=404, detail="Service not found")

    from app.services.checker import perform_service_check

    check = perform_service_check(db, id)
    return CheckOut.model_validate(check, from_attributes=True)


@router.get("/{id}/checks", response_model=list[CheckOut])
def list_service_checks(id: int, db: Session = Depends(get_db)) -> list[CheckOut]:
    service = db.query(Service).filter(Service.id == id).first()
    if not service:
        raise HTTPException(status_code=404, detail="Service not found")
    data = db.query(ServerCheck).filter(ServerCheck.service_id == id).all()
    return [CheckOut.model_validate(item, from_attributes=True) for item in data]


@router.get("/{id}/dashboard", response_model=ServiceDashboard)
def get_dashboard(id: int, db: Session = Depends(get_db)) -> ServiceDashboard:
    service = db.query(Service).filter(Service.id == id).first()
    if not service:
        raise HTTPException(status_code=404, detail="Service not found")

    svc_checks = (
        db.query(ServerCheck)
        .filter(ServerCheck.service_id == id)
        .order_by(ServerCheck.created_at.desc())
        .all()
    )
    svc_events = (
        db.query(ClientEvent)
        .filter(ClientEvent.service_id == id)
        .order_by(ClientEvent.created_at.desc())
        .all()
    )

    recent_checks_raw = svc_checks[:RECENT_ITEMS_LIMIT]
    recent_events_raw = svc_events[:RECENT_ITEMS_LIMIT]

    total_checks = len(svc_checks)
    ok_checks = sum(1 for item in svc_checks if item.is_available)
    fail_checks = total_checks - ok_checks
    avg_response = (sum(item.response_time_ms for item in svc_checks) / total_checks if total_checks else 0.0)
    uptime = (ok_checks / total_checks * 100.0) if total_checks else 0.0

    last_check = svc_checks[0] if svc_checks else None
    current_status = calculate_service_status(last_check, recent_events_raw)

    return ServiceDashboard(
        service_id=id,
        current_status=current_status,
        total_checks=total_checks,
        ok_checks=ok_checks,
        fail_checks=fail_checks,
        uptime_percent=round(uptime, 2),
        avg_response_time_ms=round(avg_response, 2),
        total_events=len(svc_events),
        recent_checks=[CheckOut.model_validate(item, from_attributes=True) for item in recent_checks_raw],
        recent_events=[ClientEventOut.model_validate(item, from_attributes=True) for item in recent_events_raw],
    )
