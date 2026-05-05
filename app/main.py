"""Application entrypoint module for the MVP web app."""

from fastapi import Depends, FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.auth import ensure_default_admin, get_current_admin
from app.database import SessionLocal, init_db
from app.models import AdminUser

from app.routers import admin, checks, client_events, demo_api, services

app = FastAPI(title="MonAmogus MVP")
app.mount("/static", StaticFiles(directory="app/static"), name="static")

app.include_router(services.router)
app.include_router(services.web_router)
app.include_router(checks.router)
app.include_router(client_events.router)
app.include_router(admin.router)
app.include_router(demo_api.router)


@app.get("/health")
def healthcheck() -> dict[str, str]:
    """Simple healthcheck endpoint."""
    return {"status": "ok"}


@app.on_event("startup")
def on_startup() -> None:
    """Initialize database schema on application startup."""
    init_db()
    db = SessionLocal()
    try:
        ensure_default_admin(db)
    finally:
        db.close()


@app.get("/demo", response_class=FileResponse)
def demo_page(admin: AdminUser = Depends(get_current_admin)) -> FileResponse:
    return FileResponse("demo/demo.html")