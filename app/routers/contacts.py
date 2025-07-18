from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session
from typing import Any, Dict, List, Optional
import csv
import io
import re
from app.database import get_db
from app.models import User
from app.schema.contact import Contact, ContactCreate, ContactUpdate, ContactImport
from app.services.contact_service import ContactService
from app.dependencies import get_current_active_user, get_current_contact_manager

router = APIRouter(prefix="/contacts", tags=["contacts"])

@router.get("", response_model=List[Contact])
async def get_contacts(
    skip: int = 0,
    limit: int = 1000,
    search: Optional[str] = None,
    status: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_contact_manager) # Apply new authorization
):
    service = ContactService(db)
    return service.get_contacts(skip=skip, limit=limit, search=search, status=status)

@router.post("", response_model=Contact)
async def create_contact(
    contact: ContactCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_contact_manager) # Apply new authorization
):
    service = ContactService(db)
    try:
        return service.create_contact(contact)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/add-list", response_model=Dict[str, Any]) # New endpoint for adding list of contacts
async def add_contacts_from_list(
    contact_import: ContactImport,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_contact_manager) # Apply new authorization
):
    service = ContactService(db)
    imported_count = 0
    skipped_count = 0
    errors = []

    for contact_data in contact_import.contacts:
        try:
            service.create_contact(contact_data)
            imported_count += 1
        except ValueError as e:
            skipped_count += 1
            errors.append({
                'contact': contact_data.name or contact_data.phone,
                'error': str(e)
            })
        except Exception as e:
            skipped_count += 1
            errors.append({
                'contact': contact_data.name or contact_data.phone,
                'error': f"Unexpected error: {str(e)}"
            })
            
    result = {
        'success': True,
        'imported_count': imported_count,
        'skipped_count': skipped_count,
        'total_contacts_in_list': len(contact_import.contacts),
        'errors': errors
    }
    
    if errors:
        result['message'] = f"Imported {imported_count} contacts, skipped {skipped_count} due to errors or duplicates."
    else:
        result['message'] = f"Successfully imported {imported_count} contacts. Skipped {skipped_count} duplicates."
        
    return result

@router.put("/{contact_id}", response_model=Contact)
async def update_contact(
    contact_id: int,
    contact: ContactUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_contact_manager) # Apply new authorization
):
    service = ContactService(db)
    try:
        updated_contact = service.update_contact(contact_id, contact)
        if not updated_contact:
            raise HTTPException(status_code=404, detail="Contact not found")
        return updated_contact
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# Removed parse_csv_contacts and parse_vcf_contacts as they are not used directly by endpoints
# and CSV import is deferred. VCF import is handled by service directly.

@router.post("/import", response_model=Dict[str, Any]) # This endpoint was for JSON list import, now /add-list handles it.
# Renaming this to /import-vcf-file to be explicit about file upload for VCF
async def import_contacts_vcf_file(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_contact_manager) # Apply new authorization
):
    service = ContactService(db)
    if not file.filename.endswith('.vcf'):
        raise HTTPException(status_code=400, detail="Only .vcf files are supported for import.")
    
    vcf_content = (await file.read()).decode('utf-8')
    result = service.import_contacts_from_vcf(vcf_content)
    
    if not result['success']:
        raise HTTPException(status_code=400, detail=result.get('error', 'VCF import failed'))
    
    return result

@router.delete("/mass-delete")
async def mass_delete_contacts(
    contact_ids: List[int],
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_contact_manager) # Apply new authorization
):
    service = ContactService(db)
    deleted_count = 0
    failed_deletions = []

    for contact_id in contact_ids:
        if service.delete_contact(contact_id):
            deleted_count += 1
        else:
            failed_deletions.append(contact_id)
    
    if failed_deletions:
        raise HTTPException(
            status_code=400,
            detail=f"Successfully deleted {deleted_count} contacts. Failed to delete contacts with IDs: {failed_deletions}"
        )
    else:
        return {"message": f"Successfully deleted {deleted_count} contacts."}

@router.delete("/{contact_id}")
async def delete_contact(
    contact_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_contact_manager) # Apply new authorization
):
    service = ContactService(db)
    if service.delete_contact(contact_id):
        return {"message": "Contact deleted successfully"}
    else:
        raise HTTPException(status_code=404, detail="Contact not found")

@router.get("/export/csv")
async def export_contacts_csv(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_contact_manager) # Apply new authorization
):
    """Export contacts to CSV format"""
    service = ContactService(db)
    contacts = service.get_contacts()
    
    # Create CSV content
    output = io.StringIO()
    fieldnames = ['name', 'phone', 'status', 'opt_out_sms', 'opt_out_whatsapp', 'metadata_']
    
    writer = csv.DictWriter(output, fieldnames=fieldnames)
    writer.writeheader()
    
    for contact in contacts:
        writer.writerow({
            'name': contact.name or '',
            'phone': contact.phone or '',
            'status': contact.status or 'active',
            'opt_out_sms': contact.opt_out_sms,
            'opt_out_whatsapp': contact.opt_out_whatsapp,
            'metadata_': contact.metadata_ or ''
        })
    
    return {
        'success': True,
        'csv_content': output.getvalue(),
        'filename': 'contacts_export.csv'
    }

@router.get("/export/vcf")
async def export_contacts_vcf(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_contact_manager) # Apply new authorization
):
    """Export contacts to VCF format"""
    service = ContactService(db)
    contacts = service.get_contacts()
    
    vcf_content = []
    
    for contact in contacts:
        vcf_entry = ['BEGIN:VCARD', 'VERSION:3.0']
        
        if contact.name:
            vcf_entry.append(f'FN:{contact.name}')
        
        if contact.phone:
            vcf_entry.append(f'TEL;TYPE=CELL:{contact.phone}')
        
        vcf_entry.append('END:VCARD')
        vcf_content.extend(vcf_entry)
        vcf_content.append('')  # Empty line between contacts
    
    return {
        'success': True,
        'vcf_content': '\n'.join(vcf_content),
        'filename': 'contacts_export.vcf'
    }
