# Church Attendance App - Offline-First Android Application

A comprehensive church management system for attendance tracking, contact management, and task scenarios. Built with Flutter using Clean Architecture, Riverpod, and Freezed.

## 🎯 Features

### 1. **Attendance System**
- QR code generation for members (only if `name != phone` AND has 'member' tag)
- Quick attendance recording via QR scanning
- Service types: Sunday, Tuesday, Special Event
- Attendance reports and filtering
- **One check-in per day per service type**

### 2. **Contact Management (Full CRUD)**
- Create, Read, Update, Delete contacts
- Tag-based filtering (member, servant, pastor, etc.)
- QR code display for eligible members
- Search by name or phone
- Offline-first with automatic sync

### 3. **Scenario/Task Management**
- Create scenarios targeting specific tags (e.g., "Food Parcel - Kanana")
- Generate TODO lists from filtered contacts
- Mark tasks as complete (tracks who completed and when)
- Prevent duplicates (completed tasks cannot be undone)
- Auto-complete scenario when all tasks done

### 4. **Offline-First Synchronization**
- Local SQLite database (Drift)
- Automatic sync when internet available
- Manual sync button
- Visual sync status indicators
- Conflict resolution: Server wins

---

## 🏗️ Architecture

```
lib/
├── core/
│   ├── database/         # Drift SQLite database
│   ├── network/          # Dio HTTP client
│   ├── sync/            # Sync manager for offline-first
│   ├── enums/           # Smart enums with UI/backend mapping
│   └── utils/           # Helpers, constants
├── features/
│   ├── auth/
│   │   ├── data/        # Repositories, data sources
│   │   ├── domain/      # Models, entities
│   │   └── presentation/# Screens, widgets, providers
│   ├── contacts/
│   ├── attendance/
│   ├── scenarios/
│   └── home/
└── main.dart
```

---

## 📦 Dependencies

```yaml
# State Management
flutter_riverpod: ^2.5.1
riverpod_annotation: ^2.3.5

# Code Generation
freezed: ^2.4.7
json_serializable: ^6.7.1

# Database (Offline-First)
drift: ^2.16.0
sqlite3_flutter_libs: ^0.5.20

# Network
dio: ^5.4.1
connectivity_plus: ^5.0.2

# QR Code
qr_flutter: ^4.1.0
mobile_scanner: ^4.0.1
```

---

## 🚀 Setup Instructions

### 1. **Clone and Install Dependencies**

```bash
cd church_attendance_app
flutter pub get
```

### 2. **Update API Base URL**

Edit `lib/core/network/api_constants.dart`:

```dart
static const String baseUrl = 'http://your-actual-api-url';
```

### 3. **Generate Code**

```bash
# Generate Freezed, JSON, Drift code
flutter pub run build_runner build --delete-conflicting-outputs
```

### 4. **Run the App**

```bash
flutter run
```

---

## 🔧 Backend Setup Required

### **Step 1: Add 'servant' Role**

Update `app/models.py`:

```python
role = Column(String(50), nullable=False)  # 'super_admin', 'secretary', 'it_admin', 'servant'
```

### **Step 2: Create New Models**

Add to `app/models.py`:

```python
class Attendance(Base):
    __tablename__ = "attendance"
    
    id = Column(Integer, primary_key=True, index=True)
    contact_id = Column(Integer, ForeignKey("contacts.id"), nullable=False)
    phone = Column(String(20), nullable=False)
    service_type = Column(String(50), nullable=False)  # 'Sunday', 'Tuesday', 'Special Event'
    service_date = Column(DateTime(timezone=True), nullable=False)
    recorded_by = Column(Integer, ForeignKey("users.id"))
    recorded_at = Column(DateTime(timezone=True), server_default=func.now())
    
    contact = relationship("Contact")
    recorder = relationship("User")

class Scenario(Base):
    __tablename__ = "scenarios"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False)
    description = Column(Text)
    filter_tags = Column(ARRAY(String))  # ['kanana'] or ['member', 'kanana']
    status = Column(String(20), default='active')  # 'active', 'completed'
    created_by = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True))
    
    tasks = relationship("ScenarioTask", back_populates="scenario")
    creator = relationship("User")

class ScenarioTask(Base):
    __tablename__ = "scenario_tasks"
    
    id = Column(Integer, primary_key=True, index=True)
    scenario_id = Column(Integer, ForeignKey("scenarios.id"), nullable=False)
    contact_id = Column(Integer, ForeignKey("contacts.id"), nullable=False)
    phone = Column(String(20), nullable=False)
    name = Column(String(200))
    is_completed = Column(Boolean, default=False)
    completed_by = Column(Integer, ForeignKey("users.id"))
    completed_at = Column(DateTime(timezone=True))
    
    scenario = relationship("Scenario", back_populates="tasks")
    contact = relationship("Contact")
    completer = relationship("User")
```

### **Step 3: Create Database Migration**

```bash
alembic revision --autogenerate -m "Add attendance, scenarios, and scenario_tasks tables"
alembic upgrade head
```

### **Step 4: Create API Endpoints**

#### **File: `app/routers/attendance.py`**

```python
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import and_, func
from typing import List, Optional
from datetime import datetime, date
from app.database import get_db
from app.models import Attendance, Contact, User
from pydantic import BaseModel

router = APIRouter(prefix="/attendance", tags=["attendance"])

class AttendanceCreate(BaseModel):
    contact_id: int
    phone: str
    service_type: str  # 'Sunday', 'Tuesday', 'Special Event'
    service_date: datetime
    recorded_by: int

class AttendanceResponse(BaseModel):
    id: int
    contact_id: int
    phone: str
    service_type: str
    service_date: datetime
    recorded_by: int
    recorded_at: datetime

    class Config:
        from_attributes = True

@router.post("/record", response_model=AttendanceResponse)
def record_attendance(
    attendance: AttendanceCreate,
    db: Session = Depends(get_db)
):
    # Check if already checked in today for this service
    service_date_only = attendance.service_date.date()
    existing = db.query(Attendance).filter(
        and_(
            Attendance.contact_id == attendance.contact_id,
            Attendance.service_type == attendance.service_type,
            func.date(Attendance.service_date) == service_date_only
        )
    ).first()
    
    if existing:
        raise HTTPException(
            status_code=400,
            detail=f"Attendance already recorded for this contact on {service_date_only} for {attendance.service_type}"
        )
    
    new_attendance = Attendance(**attendance.dict())
    db.add(new_attendance)
    db.commit()
    db.refresh(new_attendance)
    return new_attendance

@router.get("/records", response_model=List[AttendanceResponse])
def get_attendance_records(
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
    service_type: Optional[str] = None,
    contact_id: Optional[int] = None,
    db: Session = Depends(get_db)
):
    query = db.query(Attendance)
    
    if date_from:
        query = query.filter(Attendance.service_date >= date_from)
    if date_to:
        query = query.filter(Attendance.service_date <= date_to)
    if service_type:
        query = query.filter(Attendance.service_type == service_type)
    if contact_id:
        query = query.filter(Attendance.contact_id == contact_id)
    
    return query.order_by(Attendance.service_date.desc()).all()

@router.get("/summary")
def get_attendance_summary(
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
    db: Session = Depends(get_db)
):
    query = db.query(Attendance)
    
    if date_from:
        query = query.filter(Attendance.service_date >= date_from)
    if date_to:
        query = query.filter(Attendance.service_date <= date_to)
    
    total_count = query.count()
    
    by_service_type = db.query(
        Attendance.service_type,
        func.count(Attendance.id).label('count')
    ).group_by(Attendance.service_type).all()
    
    return {
        "total_attendance": total_count,
        "by_service_type": {item[0]: item[1] for item in by_service_type}
    }
```

#### **File: `app/routers/scenarios.py`**

```python
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from app.database import get_db
from app.models import Scenario, ScenarioTask, Contact
from pydantic import BaseModel
from datetime import datetime

router = APIRouter(prefix="/scenarios", tags=["scenarios"])

class ScenarioCreate(BaseModel):
    name: str
    description: Optional[str] = None
    filter_tags: List[str]
    created_by: int

class ScenarioResponse(BaseModel):
    id: int
    name: str
    description: Optional[str]
    filter_tags: List[str]
    status: str
    created_by: int
    created_at: datetime
    completed_at: Optional[datetime]

    class Config:
        from_attributes = True

class ScenarioTaskResponse(BaseModel):
    id: int
    scenario_id: int
    contact_id: int
    phone: str
    name: Optional[str]
    is_completed: bool
    completed_by: Optional[int]
    completed_at: Optional[datetime]

    class Config:
        from_attributes = True

@router.post("/", response_model=ScenarioResponse)
def create_scenario(
    scenario: ScenarioCreate,
    db: Session = Depends(get_db)
):
    # Create scenario
    new_scenario = Scenario(**scenario.dict())
    db.add(new_scenario)
    db.commit()
    db.refresh(new_scenario)
    
    # Get contacts matching filter tags
    import json
    contacts = db.query(Contact).filter(Contact.is_deleted == False).all()
    
    matching_contacts = []
    for contact in contacts:
        if contact.metadata_:
            try:
                metadata = json.loads(contact.metadata_)
                contact_tags = metadata.get('tags', [])
                if any(tag in contact_tags for tag in scenario.filter_tags):
                    matching_contacts.append(contact)
            except:
                pass
    
    # Create tasks for matching contacts
    for contact in matching_contacts:
        task = ScenarioTask(
            scenario_id=new_scenario.id,
            contact_id=contact.id,
            phone=contact.phone,
            name=contact.name
        )
        db.add(task)
    
    db.commit()
    return new_scenario

@router.get("/", response_model=List[ScenarioResponse])
def get_scenarios(
    status: Optional[str] = None,
    db: Session = Depends(get_db)
):
    query = db.query(Scenario).filter(Scenario.is_deleted == False)
    
    if status:
        query = query.filter(Scenario.status == status)
    
    return query.order_by(Scenario.created_at.desc()).all()

@router.get("/{scenario_id}", response_model=ScenarioResponse)
def get_scenario(scenario_id: int, db: Session = Depends(get_db)):
    scenario = db.query(Scenario).filter(Scenario.id == scenario_id).first()
    if not scenario:
        raise HTTPException(status_code=404, detail="Scenario not found")
    return scenario

@router.get("/{scenario_id}/tasks", response_model=List[ScenarioTaskResponse])
def get_scenario_tasks(scenario_id: int, db: Session = Depends(get_db)):
    return db.query(ScenarioTask).filter(
        ScenarioTask.scenario_id == scenario_id
    ).all()

@router.put("/{scenario_id}/tasks/{task_id}/complete")
def complete_task(
    scenario_id: int,
    task_id: int,
    completed_by: int,
    db: Session = Depends(get_db)
):
    task = db.query(ScenarioTask).filter(
        ScenarioTask.id == task_id,
        ScenarioTask.scenario_id == scenario_id
    ).first()
    
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    task.is_completed = True
    task.completed_by = completed_by
    task.completed_at = datetime.now()
    
    # Check if all tasks are completed
    all_tasks = db.query(ScenarioTask).filter(
        ScenarioTask.scenario_id == scenario_id
    ).all()
    
    if all(t.is_completed for t in all_tasks):
        scenario = db.query(Scenario).filter(Scenario.id == scenario_id).first()
        scenario.status = 'completed'
        scenario.completed_at = datetime.now()
    
    db.commit()
    return {"message": "Task completed successfully"}

@router.delete("/{scenario_id}")
def delete_scenario(scenario_id: int, db: Session = Depends(get_db)):
    scenario = db.query(Scenario).filter(Scenario.id == scenario_id).first()
    if not scenario:
        raise HTTPException(status_code=404, detail="Scenario not found")
    
    scenario.is_deleted = True
    db.commit()
    return {"message": "Scenario deleted successfully"}
```

### **Step 5: Register Routers**

In `app/main.py`:

```python
from app.routers import attendance, scenarios

app.include_router(attendance.router)
app.include_router(scenarios.router)
```

---

## 📱 App Usage

### **For Servants:**

1. **Login** with servant credentials
2. **Scan QR codes** for attendance
3. **Manage contacts** (add, edit, view)
4. **Complete scenario tasks** from TODO lists
5. **Sync** when internet is available

### **Sync Behavior:**

- Auto-sync on app start (if internet available)
- Manual sync button in app
- Visual indicator shows pending sync count
- Failed syncs are retried automatically

---

## 🔐 User Roles

- **super_admin**: Full system access
- **secretary**: Manage communications, contacts
- **it_admin**: Technical administration
- **servant**: Attendance recording, task completion

---

## 📊 Smart Enums

All enums contain:
- `backendValue`: Exact string sent to/from backend
- `displayName`: User-friendly name for UI
- `icon`: Material icon for visual representation
- `color`: Associated color for UI consistency

Example:
```dart
ServiceType.sunday.backendValue    // 'Sunday'
ServiceType.sunday.displayName     // 'Sunday Service'
ServiceType.sunday.icon            // Icons.church
ServiceType.sunday.color           // Colors.blue
```

---

## 🎨 Next Steps

1. Run `flutter pub run build_runner build` to generate code
2. Update `ApiConstants.baseUrl` with your backend URL
3. Implement remaining UI screens (login, home, contacts list, etc.)
4. Test offline-first synchronization
5. Add proper error handling and loading states

---

## 📝 Notes

- App is **Android-only** (iOS excluded in configuration)
- **Offline-first**: All operations work offline and sync later
- **Tags in metadata**: Contact tags stored in `metadata_` JSON column
- **QR eligibility**: Only contacts with `name != phone` AND 'member' tag get QR codes
- **One check-in per day**: Duplicate attendance prevented per service type per day

---

**Built with ❤️ for church management**
