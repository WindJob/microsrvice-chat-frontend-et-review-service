# Messaging Service Database

## PostgreSQL setup

Create the database used by the service:

```sql
CREATE DATABASE platform_db;
```

Then configure:

```env
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/platform_db
JWT_SECRET_KEY=change-this-secret
JWT_ALGORITHM=HS256
PORT=8011
```

The service creates its tables automatically on FastAPI startup with SQLAlchemy `Base.metadata.create_all(...)`.

## Tables

### conversations

Stores direct or group conversation containers.

| Column | Type | Notes |
|---|---|---|
| id | integer | Primary key |
| title | varchar(255), nullable | Optional conversation title |
| type | varchar(50) | Defaults to `direct` |
| created_at | datetime | Created timestamp |
| updated_at | datetime, nullable | Updated when messages are created |

### conversation_participants

Stores platform user IDs participating in a conversation.

| Column | Type | Notes |
|---|---|---|
| id | integer | Primary key |
| conversation_id | integer | FK to `conversations.id` |
| user_external_id | varchar(255) | Auth/user-service user id |
| joined_at | datetime | Join timestamp |
| is_muted | boolean | Defaults to false |
| last_read_at | datetime, nullable | Read cursor |

### messages

Stores conversation messages.

| Column | Type | Notes |
|---|---|---|
| id | integer | Primary key |
| conversation_id | integer | FK to `conversations.id` |
| sender_external_id | varchar(255) | Auth/user-service user id |
| body | text, nullable | Message body |
| message_type | varchar(50) | Defaults to `text` |
| created_at | datetime | Message timestamp |
| edited_at | datetime, nullable | Future edit support |
| is_deleted | boolean | Soft delete flag |

### location_snapshots

Stores optional location metadata attached to a message.

| Column | Type | Notes |
|---|---|---|
| id | integer | Primary key |
| message_id | integer | Unique FK to `messages.id` |
| latitude | float | Required |
| longitude | float | Required |
| accuracy_m | float, nullable | Accuracy in meters |
| address | varchar(500), nullable | Human-readable label |
| captured_at | datetime | Capture timestamp |
| ttl_sec | integer | Defaults to 3600 |

### message_read_receipts

Stores read confirmations per message and user.

| Column | Type | Notes |
|---|---|---|
| id | integer | Primary key |
| message_id | integer | FK to `messages.id` |
| user_external_id | varchar(255) | Auth/user-service user id |
| read_at | datetime | Read timestamp |

## Integration

- `auth-service`: JWT must contain `sub` or `user_id`; `role` is optional.
- `user-service`: `user_external_id` and `sender_external_id` are shared user IDs from the platform.
- `verification-ai-service`: no direct DB dependency today; can later use the same user IDs to attach verified document status to participants.
- `review-service`: no direct DB dependency today; frontend can show review notifications separately.

## Local development

SQLite is supported for quick local testing:

```powershell
Set-Item -Path Env:DATABASE_URL -Value "sqlite:///./dev_messaging.db"
Set-Item -Path Env:JWT_SECRET_KEY -Value "dev-secret"
py -3.10 -m uvicorn main:app --reload --host 0.0.0.0 --port 8011
```

Do not commit generated `.db` files.
