from fastapi import APIRouter, Depends, HTTPException, Form
from sqlalchemy.orm import Session
from typing import List, Optional
from app.database import get_db
from app.models import User, Communication
from app.schemas import Communication, CommunicationCreate
from app.services.communication_service import CommunicationService
from app.dependencies import get_current_active_user

router = APIRouter(prefix="/communications", tags=["communications"])

@router.get("/", response_model=List[Communication])
async def get_communications(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    service = CommunicationService(db)
    return service.get_communications()

@router.post("/", response_model=Communication)
async def create_communication(
    communication: CommunicationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    service = CommunicationService(db)
    return service.create_communication(communication, current_user.id)

@router.post("/{communication_id}/send", response_model=Communication)
async def send_communication(
    communication_id: int,
    tags: Optional[List[str]] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    service = CommunicationService(db)
    try:
        return service.send_communication(communication_id, tags)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/send-bulk", response_model=Communication)
async def send_bulk_sms(
    communication_id: int,
    phone_numbers: List[str],
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    service = CommunicationService(db)
    try:
        return service.send_bulk_sms(communication_id, phone_numbers)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/{communication_id}/status", response_model=Communication)
async def get_communication_status(
    communication_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    service = CommunicationService(db)
    communication = service.db.query(Communication).filter(
        Communication.id == communication_id
    ).first()
    
    if not communication:
        raise HTTPException(status_code=404, detail="Communication not found")
    
    return communication
