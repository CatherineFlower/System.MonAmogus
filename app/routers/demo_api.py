"""Demo-only API endpoints for standalone monitoring showcase."""

from datetime import datetime, timezone

from fastapi import APIRouter
from pydantic import BaseModel, Field

router = APIRouter(prefix="/demo-api", tags=["demo-api"])


class DemoClientEventIn(BaseModel):
    service_id: int = Field(gt=0)
    event_type: str = Field(min_length=1, max_length=120)
    payload: dict = Field(default_factory=dict)


class DemoCheckIn(BaseModel):
    mode: str = Field(pattern="^(ok|error)$")


DEMO_STATE: dict[str, object] = {
    "status": "ok",
    "checks": [],
    "events": [],
}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@router.get("/status")
def get_demo_status() -> dict[str, object]:
    checks = list(DEMO_STATE["checks"])[-10:]
    events = list(DEMO_STATE["events"])[-10:]
    return {
        "current_status": DEMO_STATE["status"],
        "latest_checks": checks,
        "latest_events": events,
    }


@router.post("/checks")
def push_demo_check(payload: DemoCheckIn) -> dict[str, object]:
    is_ok = payload.mode == "ok"
    record = {
        "id": len(DEMO_STATE["checks"]) + 1,
        "mode": payload.mode,
        "http_code": 200 if is_ok else 503,
        "latency_ms": 42 if is_ok else 1500,
        "created_at": _now_iso(),
    }
    DEMO_STATE["checks"].append(record)
    DEMO_STATE["status"] = "ok" if is_ok else "error"
    return {"ok": True, "record": record, "current_status": DEMO_STATE["status"]}


@router.post("/client-events")
def push_demo_client_event(payload: DemoClientEventIn) -> dict[str, object]:
    record = {
        "id": len(DEMO_STATE["events"]) + 1,
        "service_id": payload.service_id,
        "event_type": payload.event_type,
        "payload": payload.payload,
        "created_at": _now_iso(),
    }
    DEMO_STATE["events"].append(record)
    return {"ok": True, "record": record}
