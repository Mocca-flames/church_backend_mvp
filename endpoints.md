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
  "role": "user",
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
  "subject": "Sunday Service Reminder",
  "message": "Join us for service this Sunday at 10 AM. We look forward to seeing you!",
  "type": "sms"
}
```

**Response:**

The newly created communication object.

### `POST /communications/{communication_id}/send`

Sends a communication to a list of contacts based on tags.

**Path Parameters:**

- `communication_id`: The ID of the communication to send.

**Query Parameters:**

- `tags`: A list of tags to filter contacts by.

**Response:**

The updated communication object.

### `POST /communications/send-bulk`

Sends a communication to a list of phone numbers.

**Request Body:**

```json
{
  "communication_id": 1,
  "phone_numbers": ["+1234567890", "+0987654321"]
}
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

**Response:**

A list of contact objects.

### `POST /contacts/`

Creates a new contact.

**Request Body:**

```json
{
  "first_name": "John",
  "last_name": "Doe",
  "email": "john.doe@example.com",
  "phone_number": "+1234567890",
  "tags": ["member", "volunteer"]
}
```

**Response:**

The newly created contact object.

### `POST /contacts/import`

Imports contacts from a CSV or VCF file.

**Request Body:**

- `file`: The file to import.

**Response:**

```json
{
  "success": true,
  "message": "Contacts imported successfully"
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
