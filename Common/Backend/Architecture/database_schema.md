# Database Schema

The backend uses **MongoDB** for persistent storage.

Connection logic:

Backend/api_v2/app/db/mongo.py

This backend does **not** have a `users` collection anymore — user accounts
live in [`auth-service`](https://github.com/DBIS-Legal-LLMs/auth-service)'s
own MongoDB. Collections below reference a `user_id`/`owner_id` that's
just the `sub` claim of a JWT verified against that service; there's no
local join, only a loosely-coupled reference by id.

## Collections

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
