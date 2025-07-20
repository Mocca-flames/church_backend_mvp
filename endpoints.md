# API Endpoints

This document provides a comprehensive guide to all the available API endpoints, their functionalities, and how to use them properly.

## Authentication

After a successful login or registration, you will receive an `access_token`. This token must be included in the `Authorization` header of subsequent requests to protected endpoints. The format should be `Authorization: Bearer YOUR_ACCESS_TOKEN`.

All endpoints require a valid `Bearer` token in the `Authorization` header, except for the `/auth/login` and `/auth/register` endpoints.

### `POST /auth/login`

Authenticates a user and returns an access token.

**Request Body (form-data):**

- `username`: The user's email address.
- `password`: The user's password.

**Example using `curl`:**

```bash
curl -X POST "http://your-api-url/auth/login" \
-H "Content-Type: application/x-www-form-urlencoded" \
-d "username=user@example.com&password=your_password"
```

**Response:**

```json
{
  "access_token": "your_access_token",
  "token_type": "bearer",
  "refresh_token": "your_refresh_token"
}
```

**Example of using the obtained token:**

```bash
# Assuming you stored the access_token in a variable
ACCESS_TOKEN="your_access_token"

curl -X GET "http://your-api-url/auth/me" \
-H "Authorization: Bearer $ACCESS_TOKEN"
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

```json
{
    "email": "juniorbypassfrp@gmail.com",
    "role": "admin",
    "is_active": true,
    "id": 4,
    "created_at": "2025-07-18T23:28:55.533033Z",
    "access_token": "your_access_token",
    "token_type": "bearer"
}
```

For a successful registration, the backend is expected to return a JSON object containing:

- `access_token`: A string representing the authentication token.
- `token_type`: A string indicating the type of token (e.g., "Bearer").

**Example of using the obtained token:**

```bash
# Assuming you stored the access_token in a variable
ACCESS_TOKEN="your_access_token"

curl -X GET "http://your-api-url/auth/me" \
-H "Authorization: Bearer $ACCESS_TOKEN"
```

### `POST /auth/refresh`

Refreshes an access token using a refresh token.

**Request Body (JSON):**

```json
{
  "refresh_token": "your_refresh_token_here"
}
```

**Response:**

```json
{
  "access_token": "your_new_access_token",
  "token_type": "bearer"
}
```

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
  "phone": "0821234567",
  "status": "active",
  "opt_out_sms": false,
  "opt_out_whatsapp": false,
  "metadata_": "{\"source\": \"website_signup\"}"
}
```
*Note: `name` is now optional. If not provided, the phone number will be used as the contact name. Phone numbers will be automatically formatted to `+27XXXXXXXXX` and validated for South African format.*

**Response:**

The newly created contact object.

### `POST /contacts/add-list`

Adds a list of contacts. This endpoint is suitable for manually adding multiple contacts via a JSON array.


**Request Body:**

```json
{
  "contacts": [
    {
      "name": "Alice Smith",
      "phone": "27712345678",
      "status": "active"
    },
    {
      "name": "Bob Johnson",
      "phone": "0601234567",
      "status": "lead"
    },
    {
      "name": "Invalid Number",
      "phone": "12345"
    }
  ]
}
```
*Note: Phone numbers will be automatically formatted to `+27XXXXXXXXX` and validated for South African format. Malformed numbers will be skipped and reported.*

**Response:**

A summary of the import process.

```json
{
  "success": true,
  "imported_count": 2,
  "skipped_count": 1,
  "total_contacts_in_list": 3,
  "errors": [
    {
      "contact": "Invalid Number",
      "error": "Invalid South African phone number length: '12345'. Formatted number '+12345' must be 13 characters long (+27XXXXXXXXX)."
    }
  ],
  "message": "Imported 2 contacts, skipped 1 due to errors or duplicates."
}
```

### `PUT /contacts/{contact_id}`

Updates an existing contact.


**Path Parameters:**

- `contact_id`: The ID of the contact to update.

**Request Body:**

```json
{
  "name": "Jane Doe",
  "status": "inactive",
  "opt_out_sms": true,
  "phone": "0729876543"
}
```
*Note: `name` is now optional. Phone numbers will be automatically formatted to `+27XXXXXXXXX` and validated for South African format.*

**Response:**

The updated contact object.

### `POST /contacts/import-vcf-file`

Imports contacts from a VCF file upload.


**Request Body (form-data):**

- `file`: The VCF file to import.

**Response:**

A summary of the import process.

```json
{
  "success": true,
  "imported_count": 50,
  "failed_count": 2,
  "errors": [
    "Card for Jane Doe is missing a phone number.",
    "Error processing phone number +27123456789 for 'John Doe': Contact with phone number +27123456789 already exists."
  ]
}
```

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
  "csv_content": "name,phone,status,opt_out_sms,opt_out_whatsapp,metadata_\nJohn Doe,+27821234567,active,false,false,\n",
  "filename": "contacts_export.csv"
}
```

### `GET /contacts/export/vcf`

Exports contacts to VCF format.


**Response:**

```json
{
  "success": true,
  "vcf_content": "BEGIN:VCARD\nVERSION:3.0\nFN:John Doe\nTEL;TYPE=CELL:+27821234567\nEND:VCARD\n",
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
