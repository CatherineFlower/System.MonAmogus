"""Client events API endpoints."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import ClientEvent, Service
from app.schemas import ClientEventCreate, ClientEventOut

router = APIRouter(tags=["client-events"])


@router.post("/api/client-events", response_model=ClientEventOut, status_code=201)
def create_client_event(payload: ClientEventCreate, db: Session = Depends(get_db)) -> ClientEventOut:
    service = db.query(Service).filter(Service.id == payload.service_id).first()
    if not service:
        raise HTTPException(status_code=404, detail="Service not found")

    event = ClientEvent(
        service_id=payload.service_id,
        event_type=payload.event_type,
        payload=payload.payload,
    )
    db.add(event)
    db.commit()
    db.refresh(event)
    return ClientEventOut.model_validate(event, from_attributes=True)


@router.get("/api/services/{id}/events", response_model=list[ClientEventOut])
def list_service_events(id: int, db: Session = Depends(get_db)) -> list[ClientEventOut]:
    service = db.query(Service).filter(Service.id == id).first()
    if not service:
        raise HTTPException(status_code=404, detail="Service not found")
    data = db.query(ClientEvent).filter(ClientEvent.service_id == id).all()
    return [ClientEventOut.model_validate(item, from_attributes=True) for item in data]
