# 📚 Rodovid API Reference

**Version:** 2.1.0-crypto  
**Base URL:** `http://localhost:8000/api/v1`

---

## 🔐 Authentication

All endpoints require user identification via `X-User-ID` header (or `user_id` query parameter for some endpoints).

```http
X-User-ID: user_1
```

---

## 👤 Person Endpoints

### Create Person

**POST** `/api/v1/person`

Create a new person with E2E encrypted data.

**Request Body:**
```json
{
  "name_blob": "ENC_...",
  "birth_date_blob": "ENC_...",
  "death_date_blob": "ENC_...",
  "birth_year_approx": 1945,
  "death_year_approx": 2015,
  "gender": "M",
  "relation": "CHILD",
  "link_to_id": "person_abc123",
  "private_notes_blob": "ENC_...",
  "shared_notes_blob": "ENC_...",
  "source_ids": ["source_123"]
}
```

**Response:**
```json
{
  "success": true,
  "person_id": "person_xyz789",
  "message": "Особу створено (E2E encrypted)"
}
```

---

### Get Tree

**GET** `/api/v1/tree`

Retrieve the complete family tree for a user.

**Query Parameters:**
- `user_id` (default: "user_1")
- `for_sharing` (boolean, default: false) - Excludes private notes if true

**Response:**
```json
{
  "nodes": [
    {
      "id": "person_123",
      "name_blob": "ENC_...",
      "birth_date_blob": "ENC_...",
      "gender": "M",
      "birth_year_approx": 1945
    }
  ],
  "links": [
    {
      "source": "person_123",
      "target": "person_456",
      "type": "PARENT_OF"
    }
  ]
}
```

---

### Get Person

**GET** `/api/v1/person/{person_id}`

Get details for a specific person.

**Response:**
```json
{
  "id": "person_123",
  "name_blob": "ENC_...",
  "birth_date_blob": "ENC_...",
  "sources": [
    {
      "id": "source_123",
      "title": "Метрична книга",
      "confidence": "high"
    }
  ]
}
```

---

### Update Person

**PUT** `/api/v1/person/{person_id}`

Update person details (owner only).

**Request Body:**
```json
{
  "name_blob": "ENC_...",
  "birth_date_blob": "ENC_...",
  "gender": "F"
}
```

---

### Delete Person

**DELETE** `/api/v1/person/{person_id}`

Delete a person and cascade relationships.

**Response:**
```json
{
  "success": true,
  "message": "Person person_123 deleted"
}
```

---

## 🔍 Search Endpoints

### Magic Search (RAG)

**POST** `/api/v1/search/magic`

Search archival records using RAG.

**Request Body:**
```json
{
  "query": "мій прадід лікар Коваленко Київ 1920-х",
  "top_k": 5
}
```

**Response:**
```json
{
  "success": true,
  "query": "мій прадід лікар Коваленко Київ 1920-х",
  "results_count": 3,
  "results": [
    {
      "id": "arch_001",
      "title": "Метричний запис...",
      "content": "...",
      "confidence_score": 0.89
    }
  ]
}
```

---

## 📎 Source Endpoints

### Create Source

**POST** `/api/v1/source`

Create a historical source/document.

**Request Body:**
```json
{
  "title": "Метрична книга №123",
  "archive_ref": "ЦДІАК, ф. 123, оп. 1, спр. 456",
  "url": "https://...",
  "confidence": "high",
  "notes": "Документ про народження",
  "from_rag": true
}
```

---

### Link Source to Person

**POST** `/api/v1/source/link`

Link a source to a person.

**Request Body:**
```json
{
  "person_id": "person_123",
  "source_id": "source_456",
  "evidence_type": "birth"
}
```

---

## 🔗 Sharing Endpoints

### Create Invite

**POST** `/api/v1/share/invite`

Create a QR code invite for sharing.

**Query Parameters:**
- `user_id` (required) - Owner's user ID

**Request Body:**
```json
{
  "expires_in_hours": 24
}
```

**Response:**
```json
{
  "success": true,
  "invite_id": "inv_abc123",
  "qr_data": "rodovid://share/inv_abc123",
  "expires_at": "2025-01-XXT..."
}
```

---

### Accept Invite

**POST** `/api/v1/share/accept`

Accept an invite (recipient scans QR).

**Query Parameters:**
- `user_id` (required) - Recipient's user ID

**Request Body:**
```json
{
  "invite_id": "inv_abc123"
}
```

---

### Finalize Share

**POST** `/api/v1/share/finalize`

Complete sharing by sending encrypted Tree Key.

**Query Parameters:**
- `user_id` (required) - Owner's user ID

**Request Body:**
```json
{
  "invite_id": "inv_abc123",
  "encrypted_tree_key": "RSA_ENCRYPTED_TREE_KEY..."
}
```

---

## 🔑 Auth Endpoints

### Register User

**POST** `/api/v1/auth/register`

Register a new user with crypto keys.

**Request Body:**
```json
{
  "user_id": "user_1",
  "public_key": "-----BEGIN PUBLIC KEY-----\n...",
  "encrypted_private_key_blob": "ENC_...",
  "recovery_salt": "salt_123"
}
```

---

### Get User Public Key

**GET** `/api/v1/user/{user_id}/public_key`

Get a user's public key for sharing.

**Response:**
```json
{
  "user_id": "user_1",
  "public_key": "-----BEGIN PUBLIC KEY-----\n..."
}
```

---

## 📊 Stats Endpoint

### Get Stats

**GET** `/api/v1/stats`

Get tree statistics.

**Response:**
```json
{
  "persons": 25,
  "relations": 48,
  "sources": 12
}
```

---

## 🧪 Validation Endpoint

### Validate Person Data

**POST** `/api/v1/validate/person`

Validate person data without creating.

**Request Body:** Same as Create Person

**Response:**
```json
{
  "valid": true,
  "errors": [],
  "warnings": [
    {
      "code": "T4",
      "message": "Father might be too old"
    }
  ]
}
```

---

## ⚠️ Error Responses

All errors follow this format:

```json
{
  "detail": "Error message",
  "error": "Error code",
  "details": ["Additional details"]
}
```

**Common Status Codes:**
- `400` - Bad Request (validation failed)
- `404` - Not Found
- `422` - Unprocessable Entity (Pydantic validation)
- `500` - Internal Server Error

---

**Last Updated:** 2025-01-XX

