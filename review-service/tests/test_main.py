import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from datetime import datetime

from main import app, get_db
from models import Base


# Use in-memory SQLite for tests
SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)

TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base.metadata.create_all(bind=engine)


def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db

client = TestClient(app)


def test_health():
    """Test health check endpoint"""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"
    assert response.json()["service"] == "review-service"


def test_create_review():
    """Test creating a review"""
    review_data = {
        "order_id": "order-123",
        "provider_id": "provider-1",
        "user_id": "user-42",
        "rating": 5,
        "comment": "Excellent service!"
    }
    response = client.post("/api/reviews", json=review_data)
    assert response.status_code == 201
    data = response.json()
    assert data["rating"] == 5
    assert data["user_id"] == "user-42"
    assert data["provider_id"] == "provider-1"
    assert data["status"] in ["pending", "approved"]


def test_create_duplicate_review():
    """Test that duplicate reviews are rejected"""
    review_data = {
        "order_id": "order-456",
        "provider_id": "provider-2",
        "user_id": "user-43",
        "rating": 4,
        "comment": "Good"
    }
    # Create first review
    response1 = client.post("/api/reviews", json=review_data)
    assert response1.status_code == 201
    
    # Try to create duplicate
    response2 = client.post("/api/reviews", json=review_data)
    assert response2.status_code == 409


def test_get_provider_reviews():
    """Test fetching provider reviews"""
    review_data = {
        "order_id": "order-789",
        "provider_id": "provider-test",
        "user_id": "user-100",
        "rating": 5,
        "comment": "Great!"
    }
    client.post("/api/reviews", json=review_data)
    
    response = client.get("/api/reviews/provider/provider-test")
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 1


def test_get_provider_stats():
    """Test provider statistics"""
    # Create multiple reviews for a provider
    for i in range(3):
        review_data = {
            "order_id": f"order-stats-{i}",
            "provider_id": "provider-stats",
            "user_id": f"user-stats-{i}",
            "rating": 4 + (1 if i % 2 == 0 else 0),
            "comment": f"Review {i}"
        }
        client.post("/api/reviews", json=review_data)
    
    response = client.get("/api/reviews/stats/provider-stats")
    assert response.status_code == 200
    data = response.json()
    assert "count" in data
    assert "average_rating" in data


def test_get_notifications():
    """Test getting notifications for a provider"""
    response = client.get("/api/notifications?provider_id=provider-1")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)


def test_create_invitation():
    """Test creating a review invitation"""
    invitation_data = {
        "order_id": "order-invite-1",
        "provider_id": "provider-invite",
        "user_id": "user-invite"
    }
    response = client.post("/api/invitations", json=invitation_data)
    assert response.status_code == 201
    data = response.json()
    assert data["order_id"] == "order-invite-1"
    assert data["status"] == "pending"


def test_e2e_create_review_notification_stats():
    """End-to-end flow: create review -> notification -> stats"""
    provider_id = "provider-e2e"
    user_id = "client-e2e"
    order_id = "order-e2e-001"

    create_payload = {
        "order_id": order_id,
        "provider_id": provider_id,
        "user_id": user_id,
        "rating": 5,
        "comment": "Excellente prestation, rapide et propre."
    }

    create_response = client.post("/api/reviews", json=create_payload)
    assert create_response.status_code == 201
    review = create_response.json()
    assert review["provider_id"] == provider_id
    assert review["user_id"] == user_id
    assert review["rating"] == 5

    notifications_response = client.get(f"/api/notifications?provider_id={provider_id}")
    assert notifications_response.status_code == 200
    notifications = notifications_response.json()
    assert len(notifications) >= 1
    assert any(n["provider_id"] == provider_id for n in notifications)

    stats_response = client.get(f"/api/reviews/stats/{provider_id}")
    assert stats_response.status_code == 200
    stats = stats_response.json()
    assert stats["provider_id"] == provider_id
    assert stats["count"] >= 1
    assert stats["average_rating"] >= 5.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
