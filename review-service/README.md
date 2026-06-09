# Review Service

Microservice for managing reviews, ratings, and notifications across the platform.

## Architecture Overview

```
Order Completed
    ↓
Create Invitation
    ↓
Notify User (In-App + Email)
    ↓
User Leaves Review
    ↓
Auto-Check (Rating & Content)
    ↓
Approve or Flag for Moderation
    ↓
Update Statistics
    ↓
Notify Provider + Admin
```

## Features

### Core
- ✅ Create reviews (1-5 stars + comment)
- ✅ Edit reviews (72h window)
- ✅ Provider replies to reviews
- ✅ Review moderation (auto-flag + admin approval)
- ✅ Statistics & aggregation per provider
- ✅ Notifications (in-app, email pending)
- ✅ Review invitations after order completion
- ✅ One review per order (idempotence)

### Production-Ready
- PostgreSQL persistence
- JWT token validation
- Async background jobs (scheduled reminders, email queue)
- WebSocket support (planned)
- CORS enabled
- Health checks
- Error handling
- Unit tests

## Quick Start

### 1. Setup Environment

```bash
cd MENWORK/Menwork-backend/015/review-service
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure Database

Create a `.env` file:

```bash
cp .env.example .env
```

Edit `.env`:
```env
DATABASE_URL=postgresql://postgres:postgres@localhost/reviews_db
PORT=8006
JWT_SECRET_KEY=your-secret-key
```

Ensure PostgreSQL is running:
```bash
# On Windows (assumes PostgreSQL is installed)
psql -U postgres -c "CREATE DATABASE reviews_db;"
```

### 4. Run Service

```bash
python main.py
```

Or with Uvicorn directly:
```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8006
```

Service will be available at: `http://localhost:8006`

### 5. Run Tests

```bash
pytest tests/ -v
```

## API Endpoints

### Health
- `GET /health` - Service health check

### Reviews (CRUD)
- `POST /api/reviews` - Create review
- `GET /api/reviews/{review_id}` - Get single review
- `GET /api/reviews/provider/{provider_id}` - List provider's approved reviews
- `PATCH /api/reviews/{review_id}` - Update review (72h window)
- `DELETE /api/reviews/{review_id}` - Delete review

### Review Replies
- `POST /api/reviews/{review_id}/reply` - Provider replies to review
- `GET /api/reviews/{review_id}/replies` - Get all replies

### Moderation (Admin)
- `GET /api/admin/reviews/flagged` - List flagged reviews
- `PATCH /api/admin/reviews/{review_id}/approve` - Approve flagged review
- `PATCH /api/admin/reviews/{review_id}/reject` - Reject and remove review

### Notifications
- `GET /api/notifications` - Get user/provider notifications
- `POST /api/notifications/{notification_id}/read` - Mark as read
- `POST /api/notifications/mark-read` - Batch mark as read

### Statistics
- `GET /api/reviews/stats/{provider_id}` - Provider rating stats

### Invitations
- `POST /api/invitations` - Create invitation after order
- `GET /api/invitations/pending?user_id=X` - Get pending invitations

### Debug
- `GET /api/debug/reviews-all/{provider_id}` - All reviews (incl. pending)
- `GET /api/debug/stats` - Service debug info

## Example Usage

### Create Review

```bash
curl -X POST http://localhost:8006/api/reviews \
  -H "Content-Type: application/json" \
  -d '{
    "order_id": "order-123",
    "provider_id": "provider-1",
    "user_id": "client-42",
    "rating": 5,
    "comment": "Excellent work!"
  }'
```

### Get Provider Reviews

```bash
curl http://localhost:8006/api/reviews/provider/provider-1
```

### Get Statistics

```bash
curl http://localhost:8006/api/reviews/stats/provider-1
```

### Create Invitation

```bash
curl -X POST http://localhost:8006/api/invitations \
  -H "Content-Type: application/json" \
  -d '{
    "order_id": "order-456",
    "provider_id": "provider-1",
    "user_id": "client-42"
  }'
```

### Get Notifications

```bash
curl "http://localhost:8006/api/notifications?provider_id=provider-1"
```

## Data Model

### Review
- `id` (UUID)
- `order_id` (unique per order)
- `provider_id` (reviewed provider)
- `user_id` (review author)
- `rating` (1-5)
- `comment` (optional)
- `status` (pending | approved | rejected | flagged)
- `created_at`, `updated_at`
- `edited_until` (72h window)

### ReviewReply
- `id` (UUID)
- `review_id` (FK)
- `provider_id` (replying provider)
- `text` (response)
- `created_at`, `updated_at`

### Notification
- `id` (UUID)
- `user_id` or `provider_id`
- `type` (review_created | review_approved | provider_reply | etc.)
- `title`, `message`
- `status` (unread | read)
- `payload` (JSON metadata)
- `created_at`

### ReviewStatistics
- `provider_id` (unique)
- `total_reviews`, `average_rating`
- `rating_1_count` to `rating_5_count`
- `last_updated`

### ReviewInvitation
- `id` (UUID)
- `order_id` (unique)
- `provider_id`, `user_id`
- `status` (pending | completed | expired)
- `created_at`, `expires_at` (30 days)

## Workflow: Complete Example

1. **Order completed** → External service sends event
2. **Create invitation** → POST `/api/invitations`
   - Triggers notification to client
3. **Client leaves review** → POST `/api/reviews`
   - If rating ≥ 3: auto-approve, notify provider
   - If rating < 3: flag for moderation, notify admin
4. **Admin reviews flagged** → GET `/api/admin/reviews/flagged`
5. **Admin approves/rejects** → PATCH `/api/admin/reviews/{id}/approve` or `/reject`
6. **Provider can reply** → POST `/api/reviews/{id}/reply`
   - Notifies review author
7. **Statistics auto-updated** → Aggregate ratings visible at `/api/reviews/stats/{provider_id}`

## Integration Points

### With Auth Service
- Validate `user_id` / `provider_id` ownership
- (Future) Use JWT from auth-service to verify identity

### With Messaging Service
- Could reuse WebSocket for real-time notifications
- For now: HTTP polling / in-app notifications

### With Geolocation Service
- (Future) Could attach location snapshots to reviews
- Not critical for MVP

### With Notification Service
- (Future) Offload email/SMS to dedicated service
- For now: in-memory notification store

## Database Migrations (if needed)

To add/modify tables:

```bash
# Drop all tables (development only!)
python -c "from db import engine; from models import Base; Base.metadata.drop_all(engine)"

# Recreate
python -c "from db import engine; from models import Base; Base.metadata.create_all(engine)"
```

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | postgresql://postgres:postgres@localhost/reviews_db | PostgreSQL connection |
| `PORT` | 8006 | Service port |
| `JWT_SECRET_KEY` | (required) | Secret for JWT validation |
| `ENVIRONMENT` | development | dev \| production |

## Testing

Run all tests:
```bash
pytest tests/ -v
```

Run specific test:
```bash
pytest tests/test_main.py::test_health -v
```

Generate coverage:
```bash
pytest tests/ --cov=. --cov-report=html
```

## Deployment

### Docker (optional)

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8006"]
```

```bash
docker build -t review-service .
docker run -e DATABASE_URL=postgresql://... -e JWT_SECRET_KEY=... -p 8006:8006 review-service
```

### Systemd (Linux)

Create `/etc/systemd/system/review-service.service`:

```ini
[Unit]
Description=Review Service
After=network.target

[Service]
Type=simple
User=www-data
WorkingDirectory=/opt/review-service
ExecStart=/opt/review-service/venv/bin/uvicorn main:app --host 0.0.0.0 --port 8006
Restart=always

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl enable review-service
sudo systemctl start review-service
```

## Future Enhancements

- [ ] Email notifications with templates
- [ ] Background job queue (Celery + Redis) for reminders
- [ ] Redis pub/sub for horizontal scaling
- [ ] WebSocket integration for real-time notifications
- [ ] Machine learning moderation (offensive content detection)
- [ ] GraphQL API alongside REST
- [ ] Rate limiting per user
- [ ] Review authenticity verification (verified purchase badge)
- [ ] Helpful votes (upvote/downvote reviews)
- [ ] Review analytics dashboard
- [ ] Scheduled tasks: expire invitations, send reminders
- [ ] Batch email digest for providers

## Support

For issues or questions:
- Check logs: `docker logs review-service` or systemd: `journalctl -u review-service`
- Debug endpoints: `/api/debug/*`
- Test health: `curl http://localhost:8006/health`

---

**Service Version**: 1.0.0  
**Last Updated**: June 1, 2026
