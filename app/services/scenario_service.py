from sqlalchemy.orm import Session
from app.models import Scenario, ScenarioTask, Contact
from app.schema.scenario import ScenarioCreate, ScenarioUpdate
from typing import List, Optional, Dict, Any
from datetime import datetime
import json


class ScenarioService:
    def __init__(self, db: Session):
        self.db = db

    def _get_contact_tags(self, contact: Contact) -> List[str]:
        """Get tags for a contact"""
        if not contact.metadata_:
            return []
        try:
            metadata = json.loads(contact.metadata_)
            return metadata.get('tags', [])
        except (json.JSONDecodeError, TypeError):
            return []

    def _filter_contacts_by_tags(self, filter_tags: List[str]) -> List[Contact]:
        """Filter contacts by tags"""
        all_contacts = self.db.query(Contact).filter(Contact.status == 'active').all()
        matching_contacts = []
        
        for contact in all_contacts:
            contact_tags = self._get_contact_tags(contact)
            if any(tag in contact_tags for tag in filter_tags):
                matching_contacts.append(contact)
        
        return matching_contacts

    def create_scenario(self, scenario: ScenarioCreate) -> Scenario:
        """Create a new scenario and generate tasks for matching contacts"""
        # Create scenario
        db_scenario = Scenario(
            name=scenario.name,
            description=scenario.description,
            filter_tags=scenario.filter_tags,
            created_by=scenario.created_by
        )
        
        try:
            self.db.add(db_scenario)
            self.db.commit()
            self.db.refresh(db_scenario)
            
            # Get contacts matching filter tags
            matching_contacts = self._filter_contacts_by_tags(scenario.filter_tags)
            
            # Create tasks for matching contacts
            for contact in matching_contacts:
                task = ScenarioTask(
                    scenario_id=db_scenario.id,
                    contact_id=contact.id,
                    phone=contact.phone,
                    name=contact.name
                )
                self.db.add(task)
            
            self.db.commit()
            self.db.refresh(db_scenario)
            return db_scenario
            
        except Exception as e:
            self.db.rollback()
            raise e

    def get_scenarios(self, status: Optional[str] = None) -> List[Scenario]:
        """Get all scenarios with optional status filter"""
        query = self.db.query(Scenario).filter(Scenario.is_deleted == False)
        
        if status:
            query = query.filter(Scenario.status == status)
        
        return query.order_by(Scenario.created_at.desc()).all()

    def get_scenario(self, scenario_id: int) -> Optional[Scenario]:
        """Get a single scenario by ID"""
        return self.db.query(Scenario).filter(
            Scenario.id == scenario_id,
            Scenario.is_deleted == False
        ).first()

    def get_scenario_tasks(self, scenario_id: int) -> List[ScenarioTask]:
        """Get all tasks for a scenario"""
        return self.db.query(ScenarioTask).filter(
            ScenarioTask.scenario_id == scenario_id
        ).all()

    def complete_task(self, scenario_id: int, task_id: int, completed_by: int) -> Dict[str, Any]:
        """Complete a task and auto-complete scenario if all tasks are done"""
        task = self.db.query(ScenarioTask).filter(
            ScenarioTask.id == task_id,
            ScenarioTask.scenario_id == scenario_id
        ).first()
        
        if not task:
            raise ValueError("Task not found")
        
        if task.is_completed:
            raise ValueError("Task is already completed")
        
        task.is_completed = True
        task.completed_by = completed_by
        task.completed_at = datetime.now()
        
        # Check if all tasks are completed
        all_tasks = self.db.query(ScenarioTask).filter(
            ScenarioTask.scenario_id == scenario_id
        ).all()
        
        scenario_completed = False
        if all(t.is_completed for t in all_tasks):
            scenario = self.db.query(Scenario).filter(Scenario.id == scenario_id).first()
            if scenario:
                scenario.status = 'completed'
                scenario.completed_at = datetime.now()
                scenario_completed = True
        
        try:
            self.db.commit()
            return {
                "message": "Task completed successfully",
                "scenario_completed": scenario_completed
            }
        except Exception as e:
            self.db.rollback()
            raise e

    def delete_scenario(self, scenario_id: int) -> bool:
        """Soft delete a scenario"""
        scenario = self.db.query(Scenario).filter(Scenario.id == scenario_id).first()
        if not scenario:
            return False
        
        scenario.is_deleted = True
        try:
            self.db.commit()
            return True
        except Exception as e:
            self.db.rollback()
            raise e

    def get_scenario_statistics(self, scenario_id: int) -> Dict[str, Any]:
        """Get statistics for a scenario"""
        scenario = self.get_scenario(scenario_id)
        if not scenario:
            raise ValueError("Scenario not found")
        
        all_tasks = self.get_scenario_tasks(scenario_id)
        total_tasks = len(all_tasks)
        completed_tasks = sum(1 for t in all_tasks if t.is_completed)
        
        return {
            "scenario_id": scenario_id,
            "scenario_name": scenario.name,
            "total_tasks": total_tasks,
            "completed_tasks": completed_tasks,
            "pending_tasks": total_tasks - completed_tasks,
            "completion_percentage": (completed_tasks / total_tasks * 100) if total_tasks > 0 else 0
        }
