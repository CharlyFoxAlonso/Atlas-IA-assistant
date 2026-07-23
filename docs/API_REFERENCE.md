# 🔌 API Reference - Atlas v4.1

Atlas exposes a REST API via FastAPI, allowing external integration with the AI system.

**Base URL:** `http://0.0.0.0:8000`

## 1. Health Check
`GET /`
Returns the system status and version.

**Response:**
```json
{
  "status": "online",
  "version": "4.1.0",
  "name": "Atlas API"
}
```

## 2. Chat Session Management

### List Chats
`GET /chats`
Retrieves all saved chat sessions.

**Response:**
`List[ChatMetadata]` where `ChatMetadata` includes `id`, `nombre`, `creado`, `motor`, `activo`, etc.

### Create Chat
`POST /chats`
Creates a new persistent chat session.

**Request Body:**
```json
{
  "nombre": "My New Chat"
}
```

### Delete Chat
`DELETE /chats/{chat_id}`
Removes a chat session and its associated JSON file.

## 3. Interaction

### Send Message (Streaming)
`POST /chat`
Sends a prompt to the brain and returns a stream of text.

**Request Body:**
```json
{
  "prompt": "What is covariance?",
  "chat_id": "optional-id",
  "motor": "atlas | prometeo | groq",
  "modelo": "optional-model-id"
}
```

**Response:** `text/plain` stream of tokens.

## 4. System Utilities

### Process Memory
`POST /memory/process`
Triggers the memory manager to analyze the current history and extract long-term memories for the user profile.

**Response:**
```json
{
  "guardados": 2,
  "errores": 0
}
```

### Capture Screen
`GET /vision/capture`
Triggers a screenshot and performs OCR extraction.

**Response:**
```json
{
  "texto": "Extracted text from screen...",
  "ruta_imagen": "path/to/capture.png"
}
```
