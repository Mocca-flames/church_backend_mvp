from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Query
from sqlalchemy.orm import Session
from typing import Any, Dict, List, Optional
from datetime import datetime
import csv
import io
import re
import os
import logging
from app.database import get_db
from app.models import User
from app.schema.contact import BulkTagRequest, Contact, ContactCreate, ContactUpdate, ContactImport, TagRequest
from app.services.contact_service import ContactService
from app.dependencies import get_current_active_user, get_current_contact_manager
from pydantic import BaseModel

# Create logs directory if it doesn't exist
logs_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'logs')
os.makedirs(logs_dir, exist_ok=True)

# Configure dedicated logger for 400 errors
error_logger = logging.getLogger('contact_400_errors')
error_logger.setLevel(logging.ERROR)

# File handler for 400 errors
error_file_handler = logging.FileHandler(os.path.join(logs_dir, 'contact_400_errors.log'))
error_file_handler.setLevel(logging.ERROR)

# Detailed formatter - simple Request/Response format
detailed_formatter = logging.Formatter(
    '%(asctime)s | %(levelname)s | Request: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
error_file_handler.setFormatter(detailed_formatter)

# Add handler if not already added (avoid duplicate handlers)
if not error_logger.handlers:
    error_logger.addHandler(error_file_handler)

router = APIRouter(prefix="/contacts", tags=["contacts"])

# Pydantic models for tag operations


@router.get("/changes", response_model=Dict[str, Any])
async def get_contacts_changes(
    start_date: datetime = Query(..., description="Start of date range (ISO 8601 format)"),
    end_date: datetime = Query(..., description="End of date range (ISO 8601 format)"),
    limit: int = Query(5000, ge=1, le=10000, description="Maximum number of contacts to return"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_contact_manager)
):
    """
    Get contacts that were created or modified within a date range.
    
    Returns:
    - new_contacts: contacts created within the range
    - modified_contacts: contacts updated within range (excluding those also created in range)
    - statistics: counts and percentages
    
    This endpoint uses proper date range filtering (both start AND end bounds).
    """
    service = ContactService(db)
    result = service.get_contacts_in_date_range(start_date, end_date, limit)
    
    # Format the response
    return {
        'date_range': {
            'start': start_date.isoformat(),
            'end': end_date.isoformat()
        },
        'new_contacts': result['new_contacts'],
        'modified_contacts': result['modified_contacts'],
        'statistics': result['statistics']
    }


@router.get("", response_model=List[Contact])
async def get_contacts(
    skip: int = 0,
    limit: int = 500,
    search: Optional[str] = None,
    status: Optional[str] = None,
    tags: Optional[List[str]] = Query(None, description="Filter contacts by tags"),
    created_after: Optional[datetime] = Query(None, description="Filter contacts created after this datetime (ISO 8601 format)"),
    created_before: Optional[datetime] = Query(None, description="Filter contacts created before this datetime (ISO 8601 format)"),
    updated_after: Optional[datetime] = Query(None, description="Filter contacts updated after this datetime (ISO 8601 format)"),
    updated_before: Optional[datetime] = Query(None, description="Filter contacts updated before this datetime (ISO 8601 format)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_contact_manager) # Apply new authorization
):
    service = ContactService(db)
    return service.get_contacts(skip=skip, limit=limit, search=search, status=status, tags=tags, 
                                 created_after=created_after, created_before=created_before,
                                 updated_after=updated_after, updated_before=updated_before)

@router.post("", response_model=Contact)
async def create_contact(
    contact: ContactCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_contact_manager)
):
    """
    Create or update a contact.
    
    This endpoint now supports upsert behavior:
    - If contact with phone exists: updates name, merges tags
    - If contact doesn't exist: creates new contact
    
    Expected payload:
    {
        "phone": "0712345678",  // Required
        "name": "John Doe",     // Optional
        "status": "active",     // Optional, default: "active"
        "tags": ["member"],    // Optional - tags are merged with existing
        "opt_out_sms": false,   // Optional, default: false
        "opt_out_whatsapp": false  // Optional, default: false
    }
    """
    service = ContactService(db)
    try:
        return service.upsert_contact(contact, created_by=current_user.id)
    except ValueError as e:
        # Handle validation errors with detailed messages
        error_msg = str(e)
        # Log the 400 error with full details
        error_logger.error(
            f"POST /contacts | Status: 400 | Request: {str(contact.model_dump())} | Response: {error_msg}"
        )
        raise HTTPException(
            status_code=400, 
            detail={
                "error": "Validation Error",
                "message": error_msg,
                "hint": "Phone number must be in South African format: 0712345678, 271234567890, or +271234567890. Also supports international formats like +1234567890."
            }
        )
    except Exception as e:
        error_msg = str(e)
        error_logger.error(
            f"POST /contacts | Status: 400 | Request: {str(contact.model_dump())} | Response: {error_msg}"
        )
        raise HTTPException(status_code=400, detail=error_msg)

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
            service.create_contact(contact_data, created_by=current_user.id)
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
        # Log the import errors
        error_logger.error(
            f"POST /contacts/add-list | Status: 400 | Request: total={len(contact_import.contacts)} contacts | Response: imported={imported_count}, skipped={skipped_count}, errors={errors}"
        )
    else:
        result['message'] = f"Successfully imported {imported_count} contacts. Skipped {skipped_count} duplicates."
        
    return result

@router.post("/sync", response_model=Dict[str, Any])
async def sync_contacts(
    contact_import: ContactImport,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_contact_manager)
):
    """
    Sync contacts from device (bulk upsert).
    
    This endpoint is designed for device sync scenarios where:
    - Device was offline with local database
    - Now syncing all contacts to server
    - Some contacts are new, some existing (by phone)
    - Contacts may have updated names and merged tags
    
    Each contact in the list will be:
    - Created if it doesn't exist (by phone)
    - Updated if it already exists (name, tags merged, status)
    
    Expected payload:
    {
        "contacts": [
            {"phone": "0712345678", "name": "John Doe", "tags": ["member"]},
            {"phone": "0821234567", "name": "Jane Doe", "tags": ["visitor"]}
        ]
    }
    
    Returns summary with synced and failed counts.
    """
    service = ContactService(db)
    
    try:
        result = service.sync_contacts(contact_import.contacts, user_id=current_user.id)
        # Log if there were any failures
        if result.get('failed_count', 0) > 0:
            error_logger.error(
                f"POST /contacts/sync | Status: 400 | Request: {len(contact_import.contacts)} contacts | Response: synced={result.get('synced_count', 0)}, failed={result.get('failed_count', 0)}, errors={result.get('errors', [])}"
            )
        return result
    except Exception as e:
        error_msg = str(e)
        error_logger.error(
            f"POST /contacts/sync | Status: 400 | Request: {len(contact_import.contacts)} contacts | Response: {error_msg}"
        )
        raise HTTPException(status_code=400, detail=error_msg)

@router.put("/mass-update", response_model=List[Contact])
async def mass_update_contacts(
    contacts: List[Dict[str, Any]],
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_contact_manager) # Apply new authorization
):
    """
    Update multiple contacts using phone numbers as identifiers.
    Each contact in the list should have a 'phone' field and other fields to update.
    """
    service = ContactService(db)
    updated_contacts = []
    errors = []

    for contact_data in contacts:
        phone = contact_data.get('phone')
        if not phone:
            errors.append({"phone": None, "error": "Phone number is required"})
            continue

        # Create a ContactUpdate object from the contact data
        try:
            contact_update = ContactUpdate(**{k: v for k, v in contact_data.items() if k != 'phone'})
        except Exception as e:
            errors.append({"phone": phone, "error": f"Invalid data: {str(e)}"})
            continue

        try:
            updated_contact = service.update_contact_by_phone(phone, contact_update, updated_by=current_user.id)
            if not updated_contact:
                errors.append({"phone": phone, "error": "Contact not found"})
            else:
                updated_contacts.append(updated_contact)
        except Exception as e:
            errors.append({"phone": phone, "error": str(e)})

    if errors:
        # Log the mass-update errors
        error_logger.error(
            f"PUT /contacts/mass-update | Status: 400 | Request: {len(contacts)} contacts | Response: updated={len(updated_contacts)}, errors={len(errors)}, error_details={errors}"
        )
        return {
            "success": False,
            "updated_contacts": updated_contacts,
            "errors": errors
        }
    else:
        return updated_contacts

@router.put("/{contact_id}", response_model=Contact)
async def update_contact(
    contact_id: int,
    contact: ContactUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_contact_manager) # Apply new authorization
):
    service = ContactService(db)
    try:
        updated_contact = service.update_contact(contact_id, contact, updated_by=current_user.id)
        if not updated_contact:
            error_logger.error(
                f"PUT /contacts/{contact_id} | Status: 404 | Request: contact_id={contact_id}, data={str(contact.model_dump(exclude_unset=True))} | Response: Contact not found"
            )
            raise HTTPException(status_code=404, detail="Contact not found")
        return updated_contact
    except HTTPException:
        raise
    except Exception as e:
        error_msg = str(e)
        # Log the 400 error with full details
        error_logger.error(
            f"PUT /contacts/{contact_id} | Status: 400 | Request: contact_id={contact_id}, data={str(contact.model_dump(exclude_unset=True))} | Response: {error_msg}"
        )
        raise HTTPException(status_code=400, detail=error_msg)

# Tag management endpoints
@router.post("/{contact_id}/tags/add", response_model=Contact)
async def add_tags_to_contact(
    contact_id: int,
    tag_request: TagRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_contact_manager)
):
    """Add tags to a specific contact"""
    service = ContactService(db)
    try:
        updated_contact = service.add_tags_to_contact(contact_id, tag_request.tags)
        if not updated_contact:
            error_logger.error(
                f"POST /contacts/{contact_id}/tags/add | Status: 404 | Request: contact_id={contact_id}, tags={tag_request.tags} | Response: Contact not found"
            )
            raise HTTPException(status_code=404, detail="Contact not found")
        return updated_contact
    except HTTPException:
        raise
    except Exception as e:
        error_msg = str(e)
        error_logger.error(
            f"POST /contacts/{contact_id}/tags/add | Status: 400 | Request: contact_id={contact_id}, tags={tag_request.tags} | Response: {error_msg}"
        )
        raise HTTPException(status_code=400, detail=error_msg)

@router.post("/{contact_id}/tags/remove", response_model=Contact)
async def remove_tags_from_contact(
    contact_id: int,
    tag_request: TagRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_contact_manager)
):
    """Remove tags from a specific contact"""
    service = ContactService(db)
    try:
        updated_contact = service.remove_tags_from_contact(contact_id, tag_request.tags)
        if not updated_contact:
            error_logger.error(
                f"POST /contacts/{contact_id}/tags/remove | Status: 404 | Request: contact_id={contact_id}, tags={tag_request.tags} | Response: Contact not found"
            )
            raise HTTPException(status_code=404, detail="Contact not found")
        return updated_contact
    except HTTPException:
        raise
    except Exception as e:
        error_msg = str(e)
        error_logger.error(
            f"POST /contacts/{contact_id}/tags/remove | Status: 400 | Request: contact_id={contact_id}, tags={tag_request.tags} | Response: {error_msg}"
        )
        raise HTTPException(status_code=400, detail=error_msg)

@router.put("/{contact_id}/tags", response_model=Contact)
async def set_contact_tags(
    contact_id: int,
    tag_request: TagRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_contact_manager)
):
    """Set tags for a contact (replaces all existing tags)"""
    service = ContactService(db)
    try:
        updated_contact = service.set_contact_tags(contact_id, tag_request.tags)
        if not updated_contact:
            error_logger.error(
                f"PUT /contacts/{contact_id}/tags | Status: 404 | Request: contact_id={contact_id}, tags={tag_request.tags} | Response: Contact not found"
            )
            raise HTTPException(status_code=404, detail="Contact not found")
        return updated_contact
    except HTTPException:
        raise
    except Exception as e:
        error_msg = str(e)
        error_logger.error(
            f"PUT /contacts/{contact_id}/tags | Status: 400 | Request: contact_id={contact_id}, tags={tag_request.tags} | Response: {error_msg}"
        )
        raise HTTPException(status_code=400, detail=error_msg)

@router.get("/{contact_id}/tags", response_model=List[str])
async def get_contact_tags(
    contact_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_contact_manager)
):
    """Get tags for a specific contact"""
    service = ContactService(db)
    tags = service.get_contact_tags(contact_id)
    if tags is None:
        raise HTTPException(status_code=404, detail="Contact not found")
    return tags

@router.get("/tags/all", response_model=List[str])
async def get_all_tags(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_contact_manager)
):
    """Get all unique tags across all contacts"""
    service = ContactService(db)
    return service.get_all_tags()

@router.get("/tags/statistics", response_model=Dict[str, int])
async def get_tag_statistics(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_contact_manager)
):
    """Get tag usage statistics (tag name -> count)"""
    service = ContactService(db)
    return service.get_tag_statistics()

@router.get("/dashboard/statistics")
async def get_dashboard_statistics(
    date_from: Optional[datetime] = Query(None, description="Start date for filtering (ISO 8601 format)"),
    date_to: Optional[datetime] = Query(None, description="End date for filtering (ISO 8601 format)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_contact_manager)
):
    """
    Get dashboard statistics including categorized tag counts and new/modified contact counts.
    
    Returns:
    - total_contacts: Total number of contacts in the database
    - new_contacts: Count of contacts created within the date range
    - modified_contacts: Count of contacts updated within the date range (excluding new)
    - locations: Tag counts for location tags (kanana, majaneng, mashemong, etc.)
    - roles: Tag counts for role tags (pastor, protocol, worshiper, usher, financier, servant)
    - membership: member vs non_member counts
    
    Query Parameters:
    - date_from: Start date (optional, defaults to 30 days ago)
    - date_to: End date (optional, defaults to now)
    """
    service = ContactService(db)
    return service.get_dashboard_statistics(date_from=date_from, date_to=date_to)

@router.delete("/locations/{location_tag}")
async def delete_location_tag(
    location_tag: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_contact_manager)
):
    """
    Delete a dynamic location tag from all contacts.
    
    This endpoint removes a location tag from all contacts that have it and returns the result.
    
    Args:
        location_tag: The location tag to delete (e.g., "unit7", "unit_7")
        
    Returns:
    - success: Whether the operation was successful
    - deleted_location: The location tag that was deleted
    - contacts_updated: Number of contacts updated
    - message: Human-readable message
    
    Note: Cannot delete hardcoded location tags (kanana, majaneng, mashemong, soshanguve, kekana)
    """
    service = ContactService(db)
    try:
        result = service.delete_location_tag(location_tag)
        return result
    except ValueError as e:
        error_logger.error(
            f"DELETE /contacts/locations/{location_tag} | Status: 400 | Response: {str(e)}"
        )
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        error_msg = str(e)
        error_logger.error(
            f"DELETE /contacts/locations/{location_tag} | Status: 500 | Response: {error_msg}"
        )
        raise HTTPException(status_code=500, detail=error_msg)

@router.post("/tags/bulk-add", response_model=Dict[str, Any])
async def bulk_add_tags(
    bulk_request: BulkTagRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_contact_manager)
):
    """Add tags to multiple contacts"""
    service = ContactService(db)
    try:
        result = service.bulk_add_tags(bulk_request.contact_ids, bulk_request.tags)
        return result
    except Exception as e:
        error_msg = str(e)
        error_logger.error(
            f"POST /contacts/tags/bulk-add | 400 Error | "
            f"contact_ids={bulk_request.contact_ids} | tags={bulk_request.tags} | error={error_msg}"
        )
        raise HTTPException(status_code=400, detail=error_msg)

@router.post("/tags/bulk-remove", response_model=Dict[str, Any])
async def bulk_remove_tags(
    bulk_request: BulkTagRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_contact_manager)
):
    """Remove tags from multiple contacts"""
    service = ContactService(db)
    try:
        result = service.bulk_remove_tags(bulk_request.contact_ids, bulk_request.tags)
        return result
    except Exception as e:
        error_msg = str(e)
        error_logger.error(
            f"POST /contacts/tags/bulk-remove | 400 Error | "
            f"contact_ids={bulk_request.contact_ids} | tags={bulk_request.tags} | error={error_msg}"
        )
        raise HTTPException(status_code=400, detail=error_msg)

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
        error_logger.error(
            f"POST /contacts/import | Status: 400 | Request: filename={file.filename} | Response: Only .vcf files are supported"
        )
        raise HTTPException(status_code=400, detail="Only .vcf files are supported for import.")
    
    vcf_content = (await file.read()).decode('utf-8')
    result = service.import_contacts_from_vcf(vcf_content)
    
    if not result['success']:
        error_logger.error(
            f"POST /contacts/import | Status: 400 | Request: filename={file.filename} | Response: {result.get('error', 'VCF import failed')}"
        )
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
        error_logger.error(
            f"DELETE /contacts/mass-delete | Status: 400 | Request: contact_ids={contact_ids} | Response: deleted={deleted_count}, failed={failed_deletions}"
        )
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
        error_logger.error(
            f"DELETE /contacts/{contact_id} | Status: 404 | Request: contact_id={contact_id} | Response: Contact not found"
        )
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
    fieldnames = ['name', 'phone', 'status', 'tags', 'opt_out_sms', 'opt_out_whatsapp', 'metadata_']
    
    writer = csv.DictWriter(output, fieldnames=fieldnames)
    writer.writeheader()
    
    for contact in contacts:
        # Get tags for this contact
        contact_tags = service._get_contact_tags(contact)
        tags_str = ','.join(contact_tags) if contact_tags else ''
        
        writer.writerow({
            'name': contact.name or '',
            'phone': contact.phone or '',
            'status': contact.status or 'active',
            'tags': tags_str,
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
