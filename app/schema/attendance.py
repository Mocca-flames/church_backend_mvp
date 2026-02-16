from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime


class AttendanceBase(BaseModel):
    contact_id: int
    phone: str
    service_type: str  # 'Sunday', 'Tuesday', 'Special Event'
    service_date: datetime


class AttendanceCreate(AttendanceBase):
    recorded_by: int


class AttendanceUpdate(BaseModel):
    service_type: Optional[str] = None
    service_date: Optional[datetime] = None


class Attendance(AttendanceBase):
    id: int
    recorded_by: Optional[int] = None
    recorded_at: datetime

    class Config:
        from_attributes = True


class AttendanceResponse(BaseModel):
    id: int
    contact_id: int
    phone: str
    service_type: str
    service_date: datetime
    recorded_by: Optional[int] = None
    recorded_at: datetime

    class Config:
        from_attributes = True


class AttendanceSummary(BaseModel):
    total_attendance: int
    by_service_type: dict
