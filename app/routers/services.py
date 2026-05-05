"""Service management API endpoints."""

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
import httpx
from sqlalchemy.orm import Session

from app.auth import get_current_admin
from app.database import get_db
from app.models import ClientEvent, ServerCheck, Service
from app.schemas import ServiceCreate, ServiceOut
from app.auth import is_admin_request
from app.models import AdminUser


router = APIRouter(prefix="/api/services", tags=["services"])
templates = Jinja2Templates(directory="app/templates")
web_router = APIRouter(tags=["web"])


def _get_public_ip() -> str:
    try:
        response = httpx.get("https://ifconfig.me/ip", timeout=3.0)
        response.raise_for_status()
        return response.text.strip()
    except httpx.HTTPError:
        return "unknown"


@web_router.get("/", response_class=HTMLResponse)
def index_page(request: Request, db: Session = Depends(get_db)) -> HTMLResponse:
    return templates.TemplateResponse(
        request,
        "index.html",
        {
            "user_ip": _get_public_ip(),
            "is_admin": is_admin_request(request, db),
        }
    )


@web_router.get("/services/{id}", response_class=HTMLResponse)
def service_detail_page(
    id: int,
    request: Request,
    db: Session = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin),  # ← ВОТ ЭТО ДОБАВИЛИ
) -> HTMLResponse:
    service = db.query(Service).filter(Service.id == id).first()
    if not service:
        raise HTTPException(status_code=404, detail="Service not found")

    checks = (
        db.query(ServerCheck)
        .filter(ServerCheck.service_id == id)
        .order_by(ServerCheck.created_at.desc())
        .limit(10)
        .all()
    )

    events = (
        db.query(ClientEvent)
        .filter(ClientEvent.service_id == id)
        .order_by(ClientEvent.created_at.desc())
        .limit(10)
        .all()
    )

    last_check = checks[0] if checks else None
    current_status = "OK" if last_check and last_check.is_available else ("FAIL" if last_check else "N/A")

    return templates.TemplateResponse(
        request,
        "service_detail.html",
        {
            "service": service,
            "checks": checks,
            "events": events,
            "current_status": current_status,
        },
    )


@web_router.post("/services/{id}/check")
def run_manual_check(id: int, db: Session = Depends(get_db)):
    service = db.query(Service).filter(Service.id == id).first()
    if not service:
        raise HTTPException(status_code=404, detail="Service not found")
    from app.services.checker import perform_service_check

    perform_service_check(db, id)
    return RedirectResponse(url=f"/services/{id}", status_code=303)


def require_admin_api(request: Request, db: Session = Depends(get_db)) -> None:
    try:
        get_current_admin(request, db)
    except HTTPException as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin authentication required") from exc


@router.post("", response_model=ServiceOut, status_code=201, dependencies=[Depends(require_admin_api)])
def create_service(payload: ServiceCreate, db: Session = Depends(get_db)) -> ServiceOut:
    service = Service(name=payload.name, url=str(payload.url))
    db.add(service)
    db.commit()
    db.refresh(service)
    return ServiceOut.model_validate(service, from_attributes=True)


@router.get("", response_model=list[ServiceOut])
def list_services(db: Session = Depends(get_db)) -> list[ServiceOut]:
    services = db.query(Service).order_by(Service.id.asc()).all()
    result: list[ServiceOut] = []
    for item in services:
        recent_checks = (
            db.query(ServerCheck)
            .filter(ServerCheck.service_id == item.id)
            .order_by(ServerCheck.created_at.desc())
            .limit(3)
            .all()
        )

        if not recent_checks:
            status_value = None
        else:
            ok_count = sum(1 for check in recent_checks if check.is_available)

            if ok_count == len(recent_checks):
                status_value = "available"
            elif ok_count == 0:
                status_value = "unavailable"
            else:
                status_value = "degraded"

        last_check = recent_checks[0] if recent_checks else None
        result.append(
            ServiceOut(
                id=item.id,
                name=item.name,
                url=item.url,
                created_at=item.created_at,
                last_check_status=status_value,
                last_check_http_code=last_check.status_code if last_check else None,
                last_check_latency_ms=last_check.response_time_ms if last_check else None,
                last_check_at=last_check.created_at if last_check else None,
                check_source="server",
            )
        )
    return result


@router.get("/{id}", response_model=ServiceOut)
def get_service(id: int, db: Session = Depends(get_db)) -> ServiceOut:
    service = db.query(Service).filter(Service.id == id).first()
    if not service:
        raise HTTPException(status_code=404, detail="Service not found")
    return ServiceOut.model_validate(service, from_attributes=True)
