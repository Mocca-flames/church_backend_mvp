from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime


class ScenarioBase(BaseModel):
    name: str
    description: Optional[str] = None
    filter_tags: List[str]


class ScenarioCreate(ScenarioBase):
    created_by: int


class ScenarioUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    filter_tags: Optional[List[str]] = None
    status: Optional[str] = None


class Scenario(ScenarioBase):
    id: int
    status: str
    is_deleted: bool
    created_by: Optional[int] = None
    created_at: datetime
    completed_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class ScenarioResponse(BaseModel):
    id: int
    name: str
    description: Optional[str]
    filter_tags: List[str]
    status: str
    created_by: Optional[int] = None
    created_at: datetime
    completed_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class ScenarioTaskBase(BaseModel):
    scenario_id: int
    contact_id: int
    phone: str
    name: Optional[str] = None


class ScenarioTaskCreate(ScenarioTaskBase):
    pass


class ScenarioTaskUpdate(BaseModel):
    is_completed: Optional[bool] = None
    completed_by: Optional[int] = None
    completed_at: Optional[datetime] = None


class ScenarioTask(BaseModel):
    id: int
    scenario_id: int
    contact_id: int
    phone: str
    name: Optional[str] = None
    is_completed: bool
    completed_by: Optional[int] = None
    completed_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class ScenarioTaskResponse(BaseModel):
    id: int
    scenario_id: int
    contact_id: int
    phone: str
    name: Optional[str] = None
    is_completed: bool
    completed_by: Optional[int] = None
    completed_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class CompleteTaskRequest(BaseModel):
    completed_by: int
