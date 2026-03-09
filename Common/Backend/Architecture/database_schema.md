# Database Schema

The backend uses **MongoDB** for persistent storage.

Connection logic:

Backend/api_v2/app/db/mongo.py

## Collections

### users

Stores user accounts.

Fields include:

- email
- username
- password_hash
- role
- preferred_llm_provider
- preferred_model
- created_at

---

### folders

Stores folder hierarchy for chat organization.

Fields:

- owner_id
- title
- parent_folder_id
- depth
- created_at

---

### chat_sessions

Stores chat sessions.

Fields:

- user_id
- folder_id
- title
- created_at
- updated_at

---

### chat_messages

Stores individual chat messages.

Fields:

- chat_id
- user_id
- role
- content
- created_at

---

## Indexes

Indexes are created during application startup in:

Backend/api_v2/app/main.py

Examples:

- folder uniqueness per parent
- chat sorting by updated_at
- message sorting by created_at

These indexes improve performance when loading chats and messages.
