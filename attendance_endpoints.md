# Attendance & Scenarios API Endpoints

This document provides a comprehensive guide to the Attendance and Scenario API endpoints, their functionalities, and authorization requirements.

## Authentication & Authorization

All endpoints in this document **require a valid Bearer token** in the Authorization header, except for the authentication endpoints (`/auth/login` and `/auth/register`).

**Header Format:**
```
Authorization: Bearer YOUR_ACCESS_TOKEN
```

### User Roles
The system supports the following user roles:
- `super_admin` - Full system access
- `secretary` - Manage communications, contacts
- `it_admin` - Technical administration
- `servant` - Attendance recording, task completion

**Note:** Currently, any active user can access these endpoints. Role-based restrictions can be added in `app/dependencies.py` if needed.

---

## Attendance Endpoints

### `POST /attendance/record`

Records attendance for a contact. Prevents duplicate check-ins for the same service on the same day.

**Headers:**
- `Authorization: Bearer YOUR_ACCESS_TOKEN`
- `Content-Type: application/json`

**Request Body:**
```json
{
  "contact_id": 123,
  "phone": "+27821234567",
  "service_type": "Sunday",
  "service_date": "2024-01-14T09:00:00Z",
  "recorded_by": 1
}
```

**Service Types:**
- `Sunday` - Sunday Service
- `Tuesday` - Tuesday Service
- `Special Event` - Special Event

**Example using curl:**
```bash
curl -X POST "http://your-api-url/attendance/record" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "contact_id": 123,
    "phone": "+27821234567",
    "service_type": "Sunday",
    "service_date": "2024-01-14T09:00:00Z",
    "recorded_by": 1
  }'
```

**Success Response (201):**
```json
{
  "id": 1,
  "contact_id": 123,
  "phone": "+27821234567",
  "service_type": "Sunday",
  "service_date": "2024-01-14T09:00:00Z",
  "recorded_by": 1,
  "recorded_at": "2024-01-14T10:30:00Z"
}
```

**Error Response (400) - Duplicate:**
```json
{
  "detail": "Attendance already recorded for this contact on 2024-01-14 for Sunday"
}
```

---

### `GET /attendance/records`

Retrieves attendance records with optional filters.

**Headers:**
- `Authorization: Bearer YOUR_ACCESS_TOKEN`

**Query Parameters (all optional):**
- `date_from` - Filter from date (ISO 8601 format)
- `date_to` - Filter to date (ISO 8601 format)
- `service_type` - Filter by service type
- `contact_id` - Filter by contact ID

**Example:**
```bash
curl -X GET "http://your-api-url/attendance/records?service_type=Sunday&date_from=2024-01-01T00:00:00Z" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

**Success Response (200):**
```json
[
  {
    "id": 1,
    "contact_id": 123,
    "phone": "+27821234567",
    "service_type": "Sunday",
    "service_date": "2024-01-14T09:00:00Z",
    "recorded_by": 1,
    "recorded_at": "2024-01-14T10:30:00Z"
  }
]
```

---

### `GET /attendance/summary`

Gets attendance summary statistics.

**Headers:**
- `Authorization: Bearer YOUR_ACCESS_TOKEN`

**Query Parameters (all optional):**
- `date_from` - Filter from date
- `date_to` - Filter to date

**Example:**
```bash
curl -X GET "http://your-api-url/attendance/summary?date_from=2024-01-01T00:00:00Z" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

**Success Response (200):**
```json
{
  "total_attendance": 150,
  "by_service_type": {
    "Sunday": 100,
    "Tuesday": 40,
    "Special Event": 10
  }
}
```

---

### `GET /attendance/contacts/{contact_id}`

Gets all attendance records for a specific contact.

**Headers:**
- `Authorization: Bearer YOUR_ACCESS_TOKEN`

**Path Parameters:**
- `contact_id` - The contact ID

**Example:**
```bash
curl -X GET "http://your-api-url/attendance/contacts/123" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

**Success Response (200):**
```json
[
  {
    "id": 1,
    "contact_id": 123,
    "phone": "+27821234567",
    "service_type": "Sunday",
    "service_date": "2024-01-14T09:00:00Z",
    "recorded_by": 1,
    "recorded_at": "2024-01-14T10:30:00Z"
  }
]
```

---

### `DELETE /attendance/{attendance_id}`

Deletes an attendance record.

**Headers:**
- `Authorization: Bearer YOUR_ACCESS_TOKEN`

**Path Parameters:**
- `attendance_id` - The attendance record ID

**Example:**
```bash
curl -X DELETE "http://your-api-url/attendance/1" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

**Success Response (200):**
```json
{
  "message": "Attendance record deleted successfully"
}
```

---

## Scenario Endpoints

### `POST /scenarios/`

Creates a new scenario and automatically generates tasks for contacts matching the filter tags.

**Headers:**
- `Authorization: Bearer YOUR_ACCESS_TOKEN`
- `Content-Type: application/json`

**Request Body:**
```json
{
  "name": "Food Parcel - Kanana",
  "description": "Distribute food parcels to kanana members",
  "filter_tags": ["kanana"],
  "created_by": 1
}
```

**Filter Tags:**
Common tags include: `member`, `servant`, `pastor`, `kanana`, `majaneng`, or any custom tags added to contacts.

**Example:**
```bash
curl -X POST "http://your-api-url/scenarios/" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Food Parcel - Kanana",
    "description": "Distribute food parcels to kanana members",
    "filter_tags": ["kanana"],
    "created_by": 1
  }'
```

**Success Response (201):**
```json
{
  "id": 1,
  "name": "Food Parcel - Kanana",
  "description": "Distribute food parcels to kanana members",
  "filter_tags": ["kanana"],
  "status": "active",
  "created_by": 1,
  "created_at": "2024-01-14T10:30:00Z",
  "completed_at": null
}
```

---

### `GET /scenarios/`

Retrieves all scenarios with optional status filter.

**Headers:**
- `Authorization: Bearer YOUR_ACCESS_TOKEN`

**Query Parameters (optional):**
- `status` - Filter by status: `active` or `completed`

**Example:**
```bash
curl -X GET "http://your-api-url/scenarios/?status=active" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

**Success Response (200):**
```json
[
  {
    "id": 1,
    "name": "Food Parcel - Kanana",
    "description": "Distribute food parcels to kanana members",
    "filter_tags": ["kanana"],
    "status": "active",
    "created_by": 1,
    "created_at": "2024-01-14T10:30:00Z",
    "completed_at": null
  }
]
```

---

### `GET /scenarios/{scenario_id}`

Gets a single scenario by ID.

**Headers:**
- `Authorization: Bearer YOUR_ACCESS_TOKEN`

**Path Parameters:**
- `scenario_id` - The scenario ID

**Example:**
```bash
curl -X GET "http://your-api-url/scenarios/1" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

---

### `GET /scenarios/{scenario_id}/tasks`

Gets all tasks for a scenario.

**Headers:**
- `Authorization: Bearer YOUR_ACCESS_TOKEN`

**Path Parameters:**
- `scenario_id` - The scenario ID

**Example:**
```bash
curl -X GET "http://your-api-url/scenarios/1/tasks" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

**Success Response (200):**
```json
[
  {
    "id": 1,
    "scenario_id": 1,
    "contact_id": 123,
    "phone": "+27821234567",
    "name": "John Doe",
    "is_completed": false,
    "completed_by": null,
    "completed_at": null
  }
]
```

---

### `GET /scenarios/{scenario_id}/statistics`

Gets statistics for a scenario (total tasks, completed, pending, completion percentage).

**Headers:**
- `Authorization: Bearer YOUR_ACCESS_TOKEN`

**Path Parameters:**
- `scenario_id` - The scenario ID

**Example:**
```bash
curl -X GET "http://your-api-url/scenarios/1/statistics" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

**Success Response (200):**
```json
{
  "scenario_id": 1,
  "scenario_name": "Food Parcel - Kanana",
  "total_tasks": 50,
  "completed_tasks": 30,
  "pending_tasks": 20,
  "completion_percentage": 60.0
}
```

---

### `PUT /scenarios/{scenario_id}/tasks/{task_id}/complete`

Marks a task as completed. When all tasks are completed, the scenario status is automatically set to `completed`.

**Headers:**
- `Authorization: Bearer YOUR_ACCESS_TOKEN`
- `Content-Type: application/json`

**Path Parameters:**
- `scenario_id` - The scenario ID
- `task_id` - The task ID

**Request Body:**
```json
{
  "completed_by": 1
}
```

**Example:**
```bash
curl -X PUT "http://your-api-url/scenarios/1/tasks/1/complete" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"completed_by": 1}'
```

**Success Response (200):**
```json
{
  "message": "Task completed successfully",
  "scenario_completed": false
}
```

**When all tasks are completed:**
```json
{
  "message": "Task completed successfully",
  "scenario_completed": true
}
```

**Error Response (400) - Already completed:**
```json
{
  "detail": "Task is already completed"
}
```

---

### `DELETE /scenarios/{scenario_id}`

Soft deletes a scenario (marks as deleted without removing from database).

**Headers:**
- `Authorization: Bearer YOUR_ACCESS_TOKEN`

**Path Parameters:**
- `scenario_id` - The scenario ID

**Example:**
```bash
curl -X DELETE "http://your-api-url/scenarios/1" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

**Success Response (200):**
```json
{
  "message": "Scenario deleted successfully"
}
```

---

## Common Error Responses

**401 Unauthorized:**
```json
{
  "detail": "Could not validate credentials"
}
```

**404 Not Found:**
```json
{
  "detail": "Scenario not found"
}
```

**500 Internal Server Error:**
```json
{
  "detail": "Internal server error message"
}
```

---

## Integration Notes for Frontend

1. **QR Code Flow for Attendance:**
   - Scan member's QR code to get their phone number
   - Look up contact by phone to get `contact_id`
   - Call `/attendance/record` with the contact details

2. **Service Types:**
   - The app should present service type as a dropdown with: Sunday, Tuesday, Special Event

3. **Scenario Task Completion:**
   - Display tasks as a TODO list for each scenario
   - When a task is marked complete, it cannot be undone (per requirements)
   - When all tasks are complete, scenario status changes to "completed" automatically

4. **Offline-First Considerations:**
   - Store attendance and task data locally
   - Sync when internet is available
   - Handle conflicts with server wins strategy
