from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from app.database import get_db
from app.models import User
from app.schema.scenario import (
    ScenarioCreate, 
    ScenarioResponse, 
    ScenarioTaskResponse,
    CompleteTaskRequest
)
from app.services.scenario_service import ScenarioService
from app.dependencies import get_current_active_user

router = APIRouter(prefix="/scenarios", tags=["scenarios"])


@router.post("/", response_model=ScenarioResponse)
def create_scenario(
    scenario: ScenarioCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Create a new scenario and generate tasks for matching contacts"""
    service = ScenarioService(db)
    try:
        return service.create_scenario(scenario)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/", response_model=List[ScenarioResponse])
def get_scenarios(
    status: Optional[str] = Query(None, description="Filter by status (active/completed)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get all scenarios with optional status filter"""
    service = ScenarioService(db)
    return service.get_scenarios(status=status)


@router.get("/{scenario_id}", response_model=ScenarioResponse)
def get_scenario(
    scenario_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get a single scenario by ID"""
    service = ScenarioService(db)
    scenario = service.get_scenario(scenario_id)
    if not scenario:
        raise HTTPException(status_code=404, detail="Scenario not found")
    return scenario


@router.get("/{scenario_id}/tasks", response_model=List[ScenarioTaskResponse])
def get_scenario_tasks(
    scenario_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get all tasks for a scenario"""
    service = ScenarioService(db)
    return service.get_scenario_tasks(scenario_id)


@router.get("/{scenario_id}/statistics")
def get_scenario_statistics(
    scenario_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get statistics for a scenario"""
    service = ScenarioService(db)
    try:
        return service.get_scenario_statistics(scenario_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.put("/{scenario_id}/tasks/{task_id}/complete")
def complete_task(
    scenario_id: int,
    task_id: int,
    request: CompleteTaskRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Complete a task and auto-complete scenario if all tasks are done"""
    service = ScenarioService(db)
    try:
        return service.complete_task(scenario_id, task_id, request.completed_by)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{scenario_id}")
def delete_scenario(
    scenario_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Soft delete a scenario"""
    service = ScenarioService(db)
    if service.delete_scenario(scenario_id):
        return {"message": "Scenario deleted successfully"}
    else:
        raise HTTPException(status_code=404, detail="Scenario not found")
