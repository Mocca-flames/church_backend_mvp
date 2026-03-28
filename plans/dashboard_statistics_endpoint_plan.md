# Plan: GET /contacts/dashboard/statistics Endpoint

## Overview
Create a new endpoint that returns categorized tag statistics for the dashboard display, including:
- Total contacts count
- Location-based tag statistics
- Role-based tag statistics  
- Membership statistics (member vs non-member)
- New contacts count (with date filtering)
- Modified contacts count (with date filtering)

## Data Source
- Contact tags are stored in the `metadata_` column as JSON string (e.g., `{"tags": ["kanana", "member"]}`)
- Use the existing `ContactService._get_contact_tags()` method to extract tags

## Tag Categorization Rules

### 1. Location Tags
- **Hardcoded**: kanana, majaneng, mashemong, soshanguve, kekana
- **Dynamic**: Any other tag that is NOT in the roles list AND NOT "member"
- Count each location tag occurrence across all contacts

### 2. Role Tags (Fixed Set)
- pastor
- protocol  
- worshiper
- usher
- financier
- servant
- Count each role tag occurrence across all contacts

### 3. Membership
- **member**: Contacts with "member" tag in their tags
- **non_member**: Contacts WITHOUT "member" tag

## Query Parameters
- `date_from` (optional): Start date for filtering new/modified contacts (ISO 8601 format)
- `date_to` (optional): End date for filtering new/modified contacts (ISO 8601 format)
- Default behavior if no dates specified: Return last 30 days of new/modified contacts

## Response Format
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

## Implementation Steps

### Step 1: Add Service Method
File: `app/services/contact_service.py`
- Add new method `get_dashboard_statistics(date_from, date_to)` that:
  1. Gets total contact count
  2. Gets all contacts and iterates to extract tags from metadata_
  3. Categorizes tags into locations, roles, membership
  4. Calculates new/modified contact counts based on date range

### Step 2: Add Router Endpoint
File: `app/routers/contacts.py`
- Add new endpoint `GET /contacts/dashboard/statistics`
- Accept optional query parameters: date_from, date_to
- Default to last 30 days if no dates provided
- Use ContactService.get_dashboard_statistics()
- Return formatted JSON response

### Step 3: Testing
- Test with various date ranges
- Verify tag categorization is correct
- Ensure "member" only appears in membership section

## Implementation Notes
- Use existing `created_at` and `updated_at` fields on Contact model
- Filter out role tags from location calculations
- "member" tag should NOT appear in roles section
- Handle null metadata_ gracefully