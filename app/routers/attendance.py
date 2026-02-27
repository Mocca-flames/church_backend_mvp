from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy.orm import Session, joinedload
from typing import List, Optional
from datetime import datetime, date, timezone, timedelta
from app.database import get_db
from app.models import User, Attendance
from app.schema.attendance import AttendanceCreate, AttendanceResponse, AttendanceSummary
from app.services.attendance_service import AttendanceService
from app.services.pdf_service import generate_attendance_pdf
from app.dependencies import get_current_active_user

router = APIRouter(prefix="/attendance", tags=["attendance"])

# SAST timezone (UTC+2)
SAST_OFFSET = timedelta(hours=2)
SAST_TIMEZONE = timezone(SAST_OFFSET)


def convert_to_sast(dt: Optional[datetime]) -> Optional[datetime]:
    """Convert a datetime to SAST (Africa/Johannesburg) timezone.
    
    If the input is naive (no timezone), assume it's already in SAST.
    If the input is UTC (Z suffix), convert to SAST.
    """
    if dt is None:
        return None
    
    if dt.tzinfo is None:
        # Naive datetime - assume SAST
        return dt.replace(tzinfo=SAST_TIMEZONE)
    
    # Convert to SAST
    return dt.astimezone(SAST_TIMEZONE)


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
    # Convert input dates to SAST
    date_from_sast = convert_to_sast(date_from)
    date_to_sast = convert_to_sast(date_to)
    return service.get_attendance_records(
        date_from=date_from_sast,
        date_to=date_to_sast,
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
    # Convert input dates to SAST
    date_from_sast = convert_to_sast(date_from)
    date_to_sast = convert_to_sast(date_to)
    return service.get_attendance_summary(date_from=date_from_sast, date_to=date_to_sast)


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
    date: Optional[date] = Query(None, description="Export for a single date (YYYY-MM-DD)"),
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
    
    Date parameters (in order of priority):
    - date: Export for a single specific date
    - date_from + date_to: Export for a date range
    
    Note: Dates are converted to SAST (Africa/Johannesburg, UTC+2) for querying.
    If sending UTC dates (with Z suffix), they will be converted to SAST.
    """
    import logging
    logger = logging.getLogger(__name__)
    
    # Handle single date parameter - convert to date range for full day
    if date:
        # Create datetime range for the entire day in SAST
        date_from_sast = datetime.combine(date, datetime.min.time()).replace(tzinfo=SAST_TIMEZONE)
        date_to_sast = datetime.combine(date, datetime.max.time()).replace(tzinfo=SAST_TIMEZONE)
        logger.warning(f"[ATTENDANCE EXPORT] Single date mode: {date} -> from={date_from_sast}, to={date_to_sast}")
    else:
        # Convert input dates to SAST for consistent querying
        date_from_sast = convert_to_sast(date_from)
        date_to_sast = convert_to_sast(date_to)
        logger.warning(f"[ATTENDANCE EXPORT] Original: date_from={date_from}, date_to={date_to}")
        logger.warning(f"[ATTENDANCE EXPORT] Converted to SAST: date_from={date_from_sast}, date_to={date_to_sast}")
    
    # Query attendance records with contact info (eager loading)
    query = db.query(Attendance).options(joinedload(Attendance.contact))
    
    if date_from_sast:
        logger.warning(f"[ATTENDANCE EXPORT] Filtering: service_date >= {date_from_sast}")
        query = query.filter(Attendance.service_date >= date_from_sast)
    if date_to_sast:
        logger.warning(f"[ATTENDANCE EXPORT] Filtering: service_date <= {date_to_sast}")
        query = query.filter(Attendance.service_date <= date_to_sast)
    if service_type:
        query = query.filter(Attendance.service_type == service_type)
    
    attendances = query.order_by(Attendance.service_date.desc()).all()
    logger.warning(f"[ATTENDANCE EXPORT] Found {len(attendances)} attendance records")
    
    # Log each record's date for debugging
    for att in attendances:
        logger.warning(f"[ATTENDANCE EXPORT] Record ID={att.id}, service_date={att.service_date}, tzinfo={att.service_date.tzinfo if att.service_date else None}")
    
    # Generate PDF
    # Format date string for PDF header
    if date:
        # Single date: "21 February 2026"
        target_date = date
        date_str = target_date.strftime('%d %B %Y')
    elif date_from_sast and date_to_sast:
        # Range: "21 February 2026 - 26 March 2026"
        date_str = f"{date_from_sast.strftime('%d %B %Y')} - {date_to_sast.strftime('%d %B %Y')}"
    else:
        date_str = None
    
    # Format service type string for PDF header
    # Single date: "Sunday Service" | Range: "Sunday Services only"
    if service_type:
        if date:
            # Single date: "Sunday Service"
            service_type_str = f"{service_type} Service"
        else:
            # Range: "Sunday Services only"
            service_type_str = f"{service_type} Services only"
    else:
        service_type_str = "All Services"
    
    logger.warning(f"[ATTENDANCE EXPORT] PDF Header: date_str={date_str}, service_type_str={service_type_str}")
    
    pdf_bytes = generate_attendance_pdf(attendances, date_str=date_str, service_type_str=service_type_str)
    
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
