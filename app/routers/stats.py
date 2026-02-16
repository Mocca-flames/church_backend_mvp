from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Dict, Any
from app.database import get_db
from app.models import User, Contact, Communication
from app.dependencies import get_current_active_user
from app.services.sms import SMS_PROVIDERS

router = APIRouter(prefix="/stats", tags=["statistics"])

@router.get("/contacts/count", response_model=Dict[str, int])
async def get_contact_count(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Returns the total number of contacts in the database.
    """
    count = db.query(Contact).count()
    return {"total_contacts": count}

@router.get("/sms/providers", response_model=Dict[str, Any])
async def get_sms_providers(
    current_user: User = Depends(get_current_active_user)
):
    """
    Returns the number and list of available SMS providers.
    """
    provider_names = list(SMS_PROVIDERS.keys())
    return {"total_providers": len(provider_names), "providers": provider_names}

@router.get("/communications/sent-count", response_model=Dict[str, int])
async def get_sent_messages_count(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Returns the total number of messages sent.
    """
    sent_count = db.query(func.sum(Communication.sent_count)).scalar()
    return {"total_messages_sent": sent_count if sent_count is not None else 0}

@router.get("/communications/failed-count", response_model=Dict[str, int])
async def get_failed_messages_count(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Returns the total number of failed messages.
    """
    failed_count = db.query(func.sum(Communication.failed_count)).scalar()
    return {"total_messages_failed": failed_count if failed_count is not None else 0}

@router.get("/communications/by-type", response_model=Dict[str, Dict[str, int]])
async def get_communications_by_type(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Returns the count of communications grouped by message type.
    """
    results = db.query(
        Communication.message_type,
        func.count(Communication.id)
    ).group_by(Communication.message_type).all()

    counts_by_type = {row.message_type: row[1] for row in results}
    return {"counts_by_type": counts_by_type}
