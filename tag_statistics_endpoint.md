# New Tag Statistics API Endpoint Specification

## DEPRECATED (To be removed)
- `GET /contacts/tags/statistics` - Will be removed

---

## New Endpoint

**Endpoint:** `GET /contacts/dashboard/statistics`

**Purpose:** Returns categorized tag statistics for the dashboard display.

**Response Format:**
```json
{
  "total_contacts": 230,
  "locations": {
    "kanana": 45,
    "majaneng": 32,
    "mashemong": 28,
    "soshanguve": 15,
    "kekana": 10,
    "pretoria": 8,
    "custom_location_1": 5
  },
  "roles": {
    "pastor": 3,
    "protocol": 5,
    "worshiper": 150,
    "usher": 12,
    "financier": 4,
    "servant": 20
  },
  "membership": {
    "member": 180,
    "non_member": 50
  }
}
```

---

## Deep Details on "New Contacts"

### What constitutes a "New Contact"?

A "new contact" is defined as a contact that was created recently. The app tracks this through the `created_at` timestamp field in the database.

### Backend Query Requirements:

1. **Date Filtering**: Support query parameters to filter by date range:
   - `date_from` - Start date (ISO 8601 format)
   - `date_to` - End date (ISO 8601 format)
   
2. **Default Behavior**: If no dates specified, return last 30 days of new contacts

3. **Example:**
   ```
   GET /contacts/dashboard/statistics?date_from=2024-01-01&date_to=2024-01-31
   ```

### New Contacts Response Field:

```json
{
  "new_contacts": {
    "count": 25,
    "date_from": "2024-01-01",
    "date_to": "2024-01-31"
  },
  "modified_contacts": {
    "count": 10,
    "date_from": "2024-01-01",
    "date_to": "2024-01-31"
  }
}
```

---

## Complete New Endpoint Response

**Endpoint:** `GET /contacts/dashboard/statistics`

**Query Parameters (all optional):**
- `date_from` - Filter from date (ISO 8601 format)
- `date_to` - Filter to date (ISO 8601 format)

**Full Response:**
```json
{
  "total_contacts": 230,
  "new_contacts": {
    "count": 25,
    "date_from": "2024-01-01",
    "date_to": "2024-01-31"
  },
  "modified_contacts": {
    "count": 10,
    "date_from": "2024-01-01",
    "date_to": "2024-01-31"
  },
  "locations": {
    "kanana": 45,
    "majaneng": 32,
    "mashemong": 28,
    "soshanguve": 15,
    "kekana": 10,
    "pretoria": 8,
    "custom_location_1": 5
  },
  "roles": {
    "pastor": 3,
    "protocol": 5,
    "worshiper": 150,
    "usher": 12,
    "financier": 4,
    "servant": 20
  },
  "membership": {
    "member": 180,
    "non_member": 50
  }
}
```

---

## Tag Categorization Rules

### 1. Location Tags
Tags that are NOT in the roles list and NOT "member":
- **Hardcoded**: kanana, majaneng, mashemong, soshanguve, kekana
- **Dynamic**: Any other tag added by users (captured as-is)

### 2. Role Tags
Fixed set of role tags:
- pastor
- protocol
- worshiper
- usher
- financier
- servant

### 3. Membership
- **member**: Contacts with "member" tag
- **non_member**: Contacts WITHOUT "member" tag

---

## Implementation Notes

### For Backend Developer:

1. **Database Query for Locations**:
   ```sql
   SELECT 
     metadata->>'tags' as tags,
     COUNT(*) as count
   FROM contacts
   WHERE status = 'active'
   GROUP BY tags;
   ```
   Then filter out role tags and "member" from results.

2. **Database Query for New Contacts**:
   ```sql
   SELECT COUNT(*) 
   FROM contacts 
   WHERE created_at BETWEEN :date_from AND :date_to;
   ```

3. **Database Query for Modified Contacts**:
   ```sql
   SELECT COUNT(*) 
   FROM contacts 
   WHERE updated_at > created_at 
   AND updated_at BETWEEN :date_from AND :date_to;
   ```

### For Flutter Developer:

The app's [`tag_statistics_provider.dart`](lib/features/contacts/presentation/providers/tag_statistics_provider.dart) will:
1. When online: Call `GET /contacts/dashboard/statistics` and parse the JSON
2. When offline: Fall back to local SQLite calculations

---

## Data Flow Diagram

```
┌─────────────────────────────────────────────────────────┐
│                    Flutter App                          │
├─────────────────────────────────────────────────────────┤
│  Online?                                                │
│    ├─ YES → GET /contacts/dashboard/statistics          │
│    │       → Parse JSON → Display Charts               │
│    │                                                   │
│    └─ NO  → Query SQLite → Calculate Loc/Role/Member  │
│            → Display Charts (show "Offline" badge)     │
└─────────────────────────────────────────────────────────┘
```

---

## Success Criteria

1. ✅ Single endpoint returns all dashboard statistics
2. ✅ Categorized data (locations, roles, membership)
3. ✅ New contacts tracking with date filtering
4. ✅ Consistent data across all clients (Flutter, Web)
5. ✅ Server-side calculation = single source of truth
6. ✅ Offline fallback = app works without internet