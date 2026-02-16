from sqlalchemy.orm import Session
from sqlalchemy import and_, func
from app.models import Attendance
from app.schema.attendance import AttendanceCreate
from typing import List, Optional, Dict, Any
from datetime import datetime, date


class AttendanceService:
    def __init__(self, db: Session):
        self.db = db

    def record_attendance(self, attendance: AttendanceCreate) -> Attendance:
        """Record attendance for a contact"""
        # Check if already checked in today for this service
        service_date_only = attendance.service_date.date()
        
        existing = self.db.query(Attendance).filter(
            and_(
                Attendance.contact_id == attendance.contact_id,
                Attendance.service_type == attendance.service_type,
                func.date(Attendance.service_date) == service_date_only
            )
        ).first()
        
        if existing:
            raise ValueError(
                f"Attendance already recorded for this contact on {service_date_only} for {attendance.service_type}"
            )
        
        db_attendance = Attendance(
            contact_id=attendance.contact_id,
            phone=attendance.phone,
            service_type=attendance.service_type,
            service_date=attendance.service_date,
            recorded_by=attendance.recorded_by
        )
        
        try:
            self.db.add(db_attendance)
            self.db.commit()
            self.db.refresh(db_attendance)
            return db_attendance
        except Exception as e:
            self.db.rollback()
            raise e

    def get_attendance_records(
        self,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        service_type: Optional[str] = None,
        contact_id: Optional[int] = None
    ) -> List[Attendance]:
        """Get attendance records with optional filtering"""
        query = self.db.query(Attendance)
        
        if date_from:
            query = query.filter(Attendance.service_date >= date_from)
        if date_to:
            query = query.filter(Attendance.service_date <= date_to)
        if service_type:
            query = query.filter(Attendance.service_type == service_type)
        if contact_id:
            query = query.filter(Attendance.contact_id == contact_id)
        
        return query.order_by(Attendance.service_date.desc()).all()

    def get_attendance_summary(
        self,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """Get attendance summary"""
        query = self.db.query(Attendance)
        
        if date_from:
            query = query.filter(Attendance.service_date >= date_from)
        if date_to:
            query = query.filter(Attendance.service_date <= date_to)
        
        total_count = query.count()
        
        by_service_type = self.db.query(
            Attendance.service_type,
            func.count(Attendance.id).label('count')
        ).group_by(Attendance.service_type).all()
        
        return {
            "total_attendance": total_count,
            "by_service_type": {item[0]: item[1] for item in by_service_type}
        }

    def get_attendance_by_contact(self, contact_id: int) -> List[Attendance]:
        """Get all attendance records for a specific contact"""
        return self.db.query(Attendance).filter(
            Attendance.contact_id == contact_id
        ).order_by(Attendance.service_date.desc()).all()

    def delete_attendance(self, attendance_id: int) -> bool:
        """Delete an attendance record"""
        attendance = self.db.query(Attendance).filter(Attendance.id == attendance_id).first()
        if attendance:
            self.db.delete(attendance)
            self.db.commit()
            return True
        return False
