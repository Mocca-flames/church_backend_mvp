# API Endpoints

This document provides a comprehensive guide to all the available API endpoints, their functionalities, and how to use them properly.

## Authentication

All endpoints require a valid `Bearer` token in the `Authorization` header, except for the `/auth/login` and `/auth/register` endpoints.

### `POST /auth/login`

Authenticates a user and returns an access token.

**Request Body:**

- `username`: The user's email address.
- `password`: The user's password.

**Response:**

```json
{
  "access_token": "your_access_token",
  "token_type": "bearer"
}
```

### `POST /auth/register`

Registers a new user.

**Request Body:**

```json
{
  "email": "user@example.com",
  "password": "your_password",
  "role": "super_admin",
  "is_active": true
}
```

**Response:**

The newly created user object.

### `GET /auth/me`

Returns the currently authenticated user's information.

**Response:**

The user object.

## Communications

### `GET /communications/`

Returns a list of all communications.

**Response:**

A list of communication objects.

### `POST /communications/`

Creates a new communication.

**Request Body:**

```json
{
  "message_type": "sms",
  "recipient_group": "all_contacts",
  "subject": "Sunday Service Reminder",
  "message": "Join us for service this Sunday at 10 AM. We look forward to seeing you!",
  "scheduled_at": "2025-07-15T10:00:00Z",
  "metadata_": "{\"campaign\": \"summer_promo\"}"
}
```

**Response:**

The newly created communication object.

### `PUT /communications/{communication_id}`

Updates an existing communication.

**Path Parameters:**

- `communication_id`: The ID of the communication to update.

**Request Body:**

```json
{
  "message_type": "whatsapp",
  "message": "Updated message for WhatsApp campaign."
}
```

**Response:**

The updated communication object.

### `POST /communications/{communication_id}/send`

Sends a communication.

**Path Parameters:**

- `communication_id`: The ID of the communication to send.

**Response:**

The updated communication object.

### `POST /communications/send-bulk`

Sends a communication to a list of phone numbers.

**Request Body (form-data):**

- `communication_id`: The ID of the communication to send.
- `phone_numbers`: A list of phone numbers to send the message to. This parameter should be repeated for each phone number.
- `provider`: Optional. The SMS provider to use (e.g., 'twilio', 'africastalking', 'smsportal', 'winsms', 'bulksms', 'clickatel').

**Example using `curl`:**

```bash
curl -X POST "http://your-api-url/communications/send-bulk" \
-H "Authorization: Bearer your_access_token" \
-F "communication_id=1" \
-F "phone_numbers=+1234567890" \
-F "phone_numbers=+0987654321"
```

**Response:**

The updated communication object.

### `GET /communications/{communication_id}/status`

Returns the status of a communication.

**Path Parameters:**

- `communication_id`: The ID of the communication.

**Response:**

The communication object.

## Contacts

### `GET /contacts/`

Returns a list of all contacts.

**Query Parameters:**

- `skip`: The number of contacts to skip.
- `limit`: The maximum number of contacts to return.
- `search`: Optional. Search term for name or phone.
- `status`: Optional. Filter by contact status (e.g., 'active', 'inactive', 'lead', 'customer').

**Response:**

A list of contact objects.

### `POST /contacts/`

Creates a new contact.

**Request Body:**

```json
{
  "name": "John Doe",
  "phone": "+1234567890",
  "status": "active",
  "opt_out_sms": false,
  "opt_out_whatsapp": false,
  "metadata_": "{\"source\": \"website_signup\"}"
}
```
*Note: `name` is now optional. If not provided, the phone number will be used as the contact name.*

**Response:**

The newly created contact object.

### `PUT /contacts/{contact_id}`

Updates an existing contact.

**Path Parameters:**

- `contact_id`: The ID of the contact to update.

**Request Body:**

```json
{
  "name": "Jane Doe",
  "status": "inactive",
  "opt_out_sms": true
}
```
*Note: `name` is now optional.*

**Response:**

The updated contact object.

### `POST /contacts/import`

Imports contacts from a CSV or VCF file.

**Request Body:**

- `file`: The file to import.

**Response:**

A summary of the import process.

```json
{
  "success": true,
  "imported_count": 50,
  "failed_count": 2,
  "errors": [
    "Row 3: Phone number already exists",
    "Row 12: Card for Jane Doe is missing a phone number."
  ]
}
```
*Note: For CSV imports, the 'name' column is now optional. If not provided, the phone number will be used as the contact name.*

### `DELETE /contacts/mass-delete`

Deletes multiple contacts by their IDs.

**Request Body:**

```json
[1, 2, 3]
```

**Response:**

```json
{
  "message": "Successfully deleted X contacts."
}
```

### `DELETE /contacts/{contact_id}`

Deletes a contact.

**Path Parameters:**

- `contact_id`: The ID of the contact to delete.

**Response:**

```json
{
  "message": "Contact deleted successfully"
}
```

### `GET /contacts/export/csv`

Exports contacts to CSV format.

**Response:**

```json
{
  "success": true,
  "csv_content": "name,phone,status,opt_out_sms,opt_out_whatsapp,metadata_\nJohn Doe,+1234567890,active,false,false,\n",
  "filename": "contacts_export.csv"
}
```

### `GET /contacts/export/vcf`

Exports contacts to VCF format.

**Response:**

```json
{
  "success": true,
  "vcf_content": "BEGIN:VCARD\nVERSION:3.0\nFN:John Doe\nTEL;TYPE=CELL:+1234567890\nEND:VCARD\n",
  "filename": "contacts_export.vcf"
}
```

## Statistics

### `GET /stats/contacts/count`

Returns the total number of contacts in the database.

**Response:**

```json
{
  "total_contacts": 123
}
```

### `GET /stats/sms/providers`

Returns the number and list of available SMS providers.

**Response:**

```json
{
  "total_providers": 6,
  "providers": ["twilio", "africastalking", "smsportal", "winsms", "bulksms", "clickatel"]
}
```

### `GET /stats/communications/sent-count`

Returns the total number of messages sent.

**Response:**

```json
{
  "total_messages_sent": 500
}
```

### `GET /stats/communications/failed-count`

Returns the total number of failed messages.

**Response:**

```json
{
  "total_messages_failed": 10
}
```

### `GET /stats/communications/by-type`

Returns the count of communications grouped by message type.

**Response:**

```json
{
  "counts_by_type": {
    "sms": 450,
    "whatsapp": 50
  }
}
