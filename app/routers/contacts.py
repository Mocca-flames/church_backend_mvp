from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session
from typing import List, Optional
from app.database import get_db
from app.models import User
from app.schemas import Contact, ContactCreate
from app.services.contact_service import ContactService
from app.dependencies import get_current_active_user

router = APIRouter(prefix="/contacts", tags=["contacts"])

@router.get("/", response_model=List[Contact])
async def get_contacts(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    service = ContactService(db)
    return service.get_contacts(skip=skip, limit=limit)

@router.post("/", response_model=Contact)
async def create_contact(
    contact: ContactCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    service = ContactService(db)
    try:
        return service.create_contact(contact)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/import")
async def import_contacts(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    service = ContactService(db)
    content = await file.read()
    
    if file.filename.endswith('.csv'):
        csv_content = content.decode('utf-8')
        result = service.import_contacts_from_csv(csv_content)
    elif file.filename.endswith(('.vcf', '.VCF')):
        vcf_content = content.decode('utf-8')
        result = service.import_contacts_from_vcf(vcf_content)
    else:
        raise HTTPException(status_code=400, detail="Only CSV and VCF files are supported")
    
    if not result['success']:
        raise HTTPException(status_code=400, detail=result['error'])
    
    return result

@router.delete("/{contact_id}")
async def delete_contact(
    contact_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    service = ContactService(db)
    if service.delete_contact(contact_id):
        return {"message": "Contact deleted successfully"}
    else:
        raise HTTPException(status_code=404, detail="Contact not found")
