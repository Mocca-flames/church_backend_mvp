from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy.orm import Session, joinedload
from typing import List, Optional
from datetime import datetime, date
from app.database import get_db
from app.models import User, Attendance
from app.schema.attendance import AttendanceCreate, AttendanceResponse, AttendanceSummary
from app.services.attendance_service import AttendanceService
from app.services.pdf_service import generate_attendance_pdf
from app.dependencies import get_current_active_user

router = APIRouter(prefix="/attendance", tags=["attendance"])


@router.post("/record", response_model=AttendanceResponse)
def record_attendance(
    attendance: AttendanceCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Record attendance for a contact"""
    service = AttendanceService(db)
    try:
        return service.record_attendance(attendance)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/records", response_model=List[AttendanceResponse])
def get_attendance_records(
    date_from: Optional[datetime] = Query(None, description="Filter from date"),
    date_to: Optional[datetime] = Query(None, description="Filter to date"),
    service_type: Optional[str] = Query(None, description="Filter by service type"),
    contact_id: Optional[int] = Query(None, description="Filter by contact ID"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get attendance records with optional filtering"""
    service = AttendanceService(db)
    return service.get_attendance_records(
        date_from=date_from,
        date_to=date_to,
        service_type=service_type,
        contact_id=contact_id
    )


@router.get("/summary", response_model=AttendanceSummary)
def get_attendance_summary(
    date_from: Optional[datetime] = Query(None, description="Filter from date"),
    date_to: Optional[datetime] = Query(None, description="Filter to date"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get attendance summary"""
    service = AttendanceService(db)
    return service.get_attendance_summary(date_from=date_from, date_to=date_to)


@router.get("/contacts/{contact_id}", response_model=List[AttendanceResponse])
def get_contact_attendance(
    contact_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get all attendance records for a specific contact"""
    service = AttendanceService(db)
    return service.get_attendance_by_contact(contact_id)


@router.delete("/{attendance_id}")
def delete_attendance(
    attendance_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Delete an attendance record"""
    service = AttendanceService(db)
    if service.delete_attendance(attendance_id):
        return {"message": "Attendance record deleted successfully"}
    else:
        raise HTTPException(status_code=404, detail="Attendance record not found")


@router.get("/export")
async def export_attendance_pdf(
    date_from: Optional[datetime] = Query(None, description="Start of date range (ISO8601)"),
    date_to: Optional[datetime] = Query(None, description="End of date range (ISO8601)"),
    service_type: Optional[str] = Query(None, description="Filter by service type (Sunday, Tuesday, etc.)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Export attendance records as PDF.
    
    Columns: Name, Location, Phone, Member
    
    Location is extracted from contact tags (kanana, majaneng, mashemong, soshanguve, kekana)
    Member status is determined by presence of 'member' tag in contact tags
    """
    # Query attendance records with contact info (eager loading)
    query = db.query(Attendance).options(joinedload(Attendance.contact))
    
    if date_from:
        query = query.filter(Attendance.service_date >= date_from)
    if date_to:
        query = query.filter(Attendance.service_date <= date_to)
    if service_type:
        query = query.filter(Attendance.service_type == service_type)
    
    attendances = query.order_by(Attendance.service_date.desc()).all()
    
    # Generate PDF
    pdf_bytes = generate_attendance_pdf(attendances)
    
    # Generate filename with current date
    filename = f"attendance_export_{date.today()}.pdf"
    
    # Return file response
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f"attachment; filename=\"{filename}\""
        }
    )
