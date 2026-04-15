from sqlalchemy.orm import Session
from sqlalchemy import and_, func
from sqlalchemy.exc import IntegrityError
from app.models import Attendance, Contact
from app.schema.attendance import AttendanceCreate
from typing import List, Optional, Dict, Any
from datetime import datetime, date
import logging
import re

logger = logging.getLogger(__name__)


class AttendanceService:
    def __init__(self, db: Session):
        self.db = db

    def _get_or_create_contact(self, phone: str) -> Contact:
        """
        Get existing contact by phone number, or create a new one if not found.
        This handles the case where mobile apps send local contact IDs that don't
        match the server's auto-generated IDs.
        """
        # Normalize phone into a canonical form for comparison/storage
        def normalize(p: str) -> str:
            if not p:
                return ""
            digits = re.sub(r"\D", "", p)
            # South African numbers (local 0XXXXXXXXX or +27XXXXXXXXX or 27XXXXXXXXX)
            if len(digits) == 10 and digits.startswith("0"):
                return "+27" + digits[1:]
            if len(digits) == 11 and digits.startswith("27"):
                return "+" + digits
            if len(digits) == 9 and digits[0] in ["6", "7", "8", "9"]:
                return "+27" + digits
            # Fallback to digits-only
            return digits

        normalized = normalize(phone)

        # Try several likely stored variants to find an existing contact
        candidates = {phone, normalized}
        # also include digits-only form
        digits_only = re.sub(r"\D", "", phone or "")
        if digits_only:
            candidates.add(digits_only)

        contact = (
            self.db.query(Contact)
            .filter(Contact.phone.in_(list(candidates)))
            .first()
        )

        if contact:
            return contact

        # Create a new contact using the normalized phone
        try:
            contact = Contact(name=normalized, phone=normalized, status="active")
            self.db.add(contact)
            self.db.commit()
            self.db.refresh(contact)
            logger.info(f"Auto-created contact {contact.id} for phone {phone}")
            return contact
        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to create contact for phone {phone}: {e}")
            raise ValueError(f"Could not find or create contact with phone {phone}")

    def record_attendance(self, attendance: AttendanceCreate) -> Attendance:
        """Record attendance for a contact"""
        # Get or create contact by phone number (handles mobile app local IDs)
        contact = self._get_or_create_contact(attendance.phone)
        contact_id = contact.id

        # Check if already checked in today for this service
        service_date_only = attendance.service_date.date()

        existing = (
            self.db.query(Attendance)
            .filter(
                and_(
                    Attendance.contact_id == contact_id,
                    Attendance.service_type == attendance.service_type,
                    func.date(Attendance.service_date) == service_date_only,
                )
            )
            .first()
        )

        if existing:
            raise ValueError(
                f"Attendance already recorded for this contact on {service_date_only} for {attendance.service_type}"
            )

        db_attendance = Attendance(
            contact_id=contact_id,
            phone=attendance.phone,
            service_type=attendance.service_type,
            service_date=attendance.service_date,
            recorded_by=attendance.recorded_by,
        )

        try:
            self.db.add(db_attendance)
            self.db.commit()
            self.db.refresh(db_attendance)
            return db_attendance
        except IntegrityError as e:
            self.db.rollback()
            if "unique_attendance_per_contact_service_date" in str(e):
                raise ValueError(
                    "Attendance already recorded for this contact on this date for this service type"
                )
            else:
                raise e
        except Exception as e:
            self.db.rollback()
            raise e

    def get_attendance_records(
        self,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        service_type: Optional[str] = None,
        contact_id: Optional[int] = None,
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
        self, date_from: Optional[datetime] = None, date_to: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """Get attendance summary"""
        query = self.db.query(Attendance)

        if date_from:
            query = query.filter(Attendance.service_date >= date_from)
        if date_to:
            query = query.filter(Attendance.service_date <= date_to)

        total_count = query.count()

        by_service_type = (
            self.db.query(
                Attendance.service_type, func.count(Attendance.id).label("count")
            )
            .group_by(Attendance.service_type)
            .all()
        )

        return {
            "total_attendance": total_count,
            "by_service_type": {item[0]: item[1] for item in by_service_type},
        }

    def get_attendance_by_contact(self, contact_id: int) -> List[Attendance]:
        """Get all attendance records for a specific contact"""
        return (
            self.db.query(Attendance)
            .filter(Attendance.contact_id == contact_id)
            .order_by(Attendance.service_date.desc())
            .all()
        )

    def delete_attendance(self, attendance_id: int) -> bool:
        """Delete an attendance record"""
        attendance = (
            self.db.query(Attendance).filter(Attendance.id == attendance_id).first()
        )
        if attendance:
            self.db.delete(attendance)
            self.db.commit()
            return True
        return False
