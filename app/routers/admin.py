"""Admin authentication and protected admin pages."""

from fastapi import APIRouter, Depends, Form, Request, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.auth import SESSION_COOKIE_NAME, build_session_cookie, ensure_default_admin, get_current_admin, verify_password
from app.database import get_db
from app.models import AdminUser, Service
from app.schemas import ServiceCreate

router = APIRouter(prefix="/admin", tags=["admin"])
templates = Jinja2Templates(directory="app/templates")


@router.get("/login", response_class=HTMLResponse)
def admin_login_page(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(request, "login.html", {"error": None})


@router.post("/login", response_class=HTMLResponse)
def admin_login_submit(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db),
):
    ensure_default_admin(db)
    admin = db.query(AdminUser).filter(AdminUser.username == username).first()
    if not admin or not verify_password(password, admin.password_hash):
        return templates.TemplateResponse(
            request,
            "login.html",
            {"error": "Неверный логин или пароль"},
            status_code=401,
        )

    response = RedirectResponse(url="/admin", status_code=303)
    response.set_cookie(SESSION_COOKIE_NAME, build_session_cookie(admin.username), httponly=True, samesite="lax")
    return response


@router.get("", response_class=HTMLResponse, dependencies=[Depends(get_current_admin)])
def admin_home(request: Request) -> HTMLResponse:
    return RedirectResponse(url="/admin/services", status_code=303)


def _service_rows(db: Session) -> list[Service]:
    return db.query(Service).order_by(Service.sort_order.asc(), Service.id.asc()).all()


@router.get("/services", response_class=HTMLResponse, dependencies=[Depends(get_current_admin)])
def admin_services_page(request: Request, db: Session = Depends(get_db)) -> HTMLResponse:
    return templates.TemplateResponse(
        request,
        "admin_services.html",
        {
            "services": _service_rows(db),
            "error": None,
            "is_admin": True,
        },
    )


@router.post("/services/create", dependencies=[Depends(get_current_admin)])
def admin_service_create(request: Request, name: str = Form(...), url: str = Form(...), description: str = Form(""), sort_order: int = Form(0), db: Session = Depends(get_db)):
    try:
        payload = ServiceCreate(name=name, url=url)
    except Exception as exc:
        return templates.TemplateResponse(request, "admin_services.html", {"services": _service_rows(db), "error": str(exc)}, status_code=400)

    service = Service(
        name=payload.name,
        url=str(payload.url),
        description=description.strip(),
        is_active=True,
        sort_order=sort_order,
    )
    db.add(service)
    db.commit()
    return RedirectResponse(url="/admin/services", status_code=303)


@router.post("/services/{service_id}/edit", dependencies=[Depends(get_current_admin)])
def admin_service_edit(request: Request, service_id: int, name: str = Form(...), url: str = Form(...), description: str = Form(""), sort_order: int = Form(0), is_active: str | None = Form(None), db: Session = Depends(get_db)):
    service = db.query(Service).filter(Service.id == service_id).first()
    if not service:
        return RedirectResponse(url="/admin/services", status_code=303)
    try:
        payload = ServiceCreate(name=name, url=url)
    except Exception as exc:
        return templates.TemplateResponse(request, "admin_services.html", {"services": _service_rows(db), "error": str(exc)}, status_code=400)
    service.name = payload.name
    service.url = str(payload.url)
    service.description = description.strip()
    service.sort_order = sort_order
    service.is_active = is_active == "on"
    db.commit()
    return RedirectResponse(url="/admin/services", status_code=303)


@router.delete(
    "/services/{service_id}",
    dependencies=[Depends(get_current_admin)]
)
def admin_service_delete(
    service_id: int,
    db: Session = Depends(get_db)
):
    service = (
        db.query(Service)
        .filter(Service.id == service_id)
        .first()
    )

    if not service:
        raise HTTPException(
            status_code=404,
            detail="Service not found"
        )

    db.delete(service)
    db.commit()

    return JSONResponse({
        "success": True,
        "deleted_id": service_id
    })

@router.get("/logout")
def admin_logout():
    response = RedirectResponse(url="/", status_code=303)
    response.delete_cookie(SESSION_COOKIE_NAME)
    return response