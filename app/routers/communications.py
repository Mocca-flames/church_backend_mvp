from fastapi import APIRouter, Depends, HTTPException, Form
from sqlalchemy.orm import Session
from typing import List, Optional
from app.database import get_db
from app.models import User, Communication
from app.schemas import Communication as CommunicationSchema, CommunicationCreate
from app.services.communication_service import CommunicationService
from app.dependencies import get_current_active_user

router = APIRouter(prefix="/communications", tags=["communications"])

@router.get("", response_model=List[CommunicationSchema])
async def get_communications(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    service = CommunicationService(db)
    return service.get_communications()

@router.post("", response_model=CommunicationSchema)
async def create_communication(
    communication: CommunicationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    service = CommunicationService(db)
    return service.create_communication(communication, current_user.id)

@router.post("/{communication_id}/send", response_model=CommunicationSchema)
async def send_communication(
    communication_id: int,
    tags: Optional[List[str]] = Form(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    service = CommunicationService(db)
    try:
        return service.send_communication(communication_id, tags)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/send-bulk", response_model=CommunicationSchema)
async def send_bulk_sms(
    communication_id: int = Form(...),
    phone_numbers: List[str] = Form(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    service = CommunicationService(db)
    try:
        return service.send_bulk_sms(communication_id, phone_numbers)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/{communication_id}/status", response_model=CommunicationSchema)
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

@router.delete("/{communication_id}")
async def delete_communication(
    communication_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    service = CommunicationService(db)
    
    # Check if communication exists
    communication = service.db.query(Communication).filter(
        Communication.id == communication_id
    ).first()
    
    if not communication:
        raise HTTPException(status_code=404, detail="Communication not found")
    
    # Optional: Add authorization check to ensure user can delete this communication
    # if communication.created_by != current_user.id:
    #     raise HTTPException(status_code=403, detail="Not authorized to delete this communication")
    
    try:
        # Delete the communication
        service.db.delete(communication)
        service.db.commit()
        return {"message": "Communication deleted successfully"}
    except Exception as e:
        service.db.rollback()
        raise HTTPException(status_code=500, detail=f"Error deleting communication: {str(e)}")
