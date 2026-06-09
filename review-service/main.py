from fastapi import FastAPI, Depends, HTTPException, Query, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from datetime import datetime
from typing import List, Optional
import uuid
import os
import logging

from db import get_db, init_db, engine
from models import Base, ReviewStatusEnum, NotificationTypeEnum
from schemas import (
    ReviewCreate, ReviewOut, ReviewListOut, ReviewUpdate, ReviewReplyCreate, ReviewReplyOut,
    NotificationOut, ReviewStatisticsOut, ReviewFlagCreate, ReviewInvitationCreate, ReviewInvitationOut
)
import crud

logger = logging.getLogger(__name__)

app = FastAPI(
    title="Review Service",
    description="Microservice for managing reviews, ratings, and notifications",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============ STARTUP ============

@app.on_event("startup")
async def startup_event():
    """Initialize database on startup"""
    logger.info("Initializing database...")
    init_db()
    logger.info("Database initialized successfully")


@app.get("/health", tags=["Health"])
async def health():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "review-service",
        "timestamp": datetime.utcnow().isoformat()
    }


# ============ REVIEWS - CREATE ============

@app.post("/api/reviews", response_model=ReviewOut, status_code=201, tags=["Reviews"])
async def create_review(review_in: ReviewCreate, db: Session = Depends(get_db)):
    """
    Create a new review for a provider
    - **order_id**: Unique order identifier
    - **provider_id**: Provider being reviewed
    - **user_id**: Customer leaving the review
    - **rating**: Rating from 1 to 5
    - **comment**: Optional review comment
    """
    # Check if review already exists for this order
    existing = crud.get_review_by_order(db, review_in.order_id)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Review already exists for this order"
        )
    
    review = crud.create_review(db, review_in)
    
    # Auto-approve if rating >= 3 (optional: add content moderation)
    if review.rating >= 3:
        review.status = ReviewStatusEnum.APPROVED
        db.commit()
        db.refresh(review)
        
        # Notify provider
        crud.create_notification(
            db,
            user_id=review.provider_id,
            notif_type=NotificationTypeEnum.REVIEW_APPROVED,
            title=f"Nouvel avis de {review.user_id}",
            message=f"Vous avez reçu un avis {review.rating}★",
            provider_id=review.provider_id,
            payload={"review_id": review.id, "rating": review.rating}
        )
        
        # Update statistics
        crud.update_provider_statistics(db, review.provider_id)
    else:
        # Flag for moderation
        crud.create_review_flag(
            db,
            review.id,
            ReviewFlagCreate(reason="low_rating", reporter_id="system")
        )
        
        # Notify admin
        crud.create_notification(
            db,
            user_id="admin",
            notif_type=NotificationTypeEnum.REVIEW_FLAGGED,
            title="Avis avec note basse détecté",
            message=f"Avis {review.rating}★ de {review.user_id} pour {review.provider_id}",
            payload={"review_id": review.id, "rating": review.rating}
        )
    
    # Mark invitation as completed
    crud.complete_invitation(db, review_in.order_id)
    
    return review


# ============ REVIEWS - READ ============

@app.get("/api/reviews/{review_id}", response_model=ReviewOut, tags=["Reviews"])
async def get_review(review_id: str, db: Session = Depends(get_db)):
    """Get a single review by ID"""
    review = crud.get_review(db, review_id)
    if not review:
        raise HTTPException(status_code=404, detail="Review not found")
    return review


@app.get("/api/reviews/provider/{provider_id}", response_model=List[ReviewListOut], tags=["Reviews"])
async def get_provider_reviews(
    provider_id: str,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """Get all approved reviews for a provider"""
    reviews = crud.get_reviews_by_provider(db, provider_id, skip, limit)
    
    # Transform to simpler response
    result = []
    for r in reviews:
        result.append(ReviewListOut(
            id=r.id,
            provider_id=r.provider_id,
            user=r.user_id,
            rating=r.rating,
            comment=r.comment,
            created_at=r.created_at,
            status=r.status
        ))
    return result


# ============ REVIEWS - UPDATE ============

@app.patch("/api/reviews/{review_id}", response_model=ReviewOut, tags=["Reviews"])
async def update_review(
    review_id: str,
    review_update: ReviewUpdate,
    db: Session = Depends(get_db)
):
    """
    Update a review (only within 72h edit window)
    """
    review = crud.update_review(db, review_id, review_update)
    if not review:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Review not found or edit window closed"
        )
    return review


# ============ REVIEWS - DELETE ============

@app.delete("/api/reviews/{review_id}", status_code=204, tags=["Reviews"])
async def delete_review(review_id: str, db: Session = Depends(get_db)):
    """Delete a review (admin only in production)"""
    success = crud.delete_review(db, review_id)
    if not success:
        raise HTTPException(status_code=404, detail="Review not found")
    return None


# ============ REVIEW REPLIES ============

@app.post("/api/reviews/{review_id}/reply", response_model=ReviewReplyOut, status_code=201, tags=["Replies"])
async def add_provider_reply(
    review_id: str,
    reply_in: ReviewReplyCreate,
    provider_id: str = Query(...),
    db: Session = Depends(get_db)
):
    """
    Add a provider's reply to a review
    - **provider_id**: Query param to identify provider (in production, extract from JWT)
    """
    review = crud.get_review(db, review_id)
    if not review:
        raise HTTPException(status_code=404, detail="Review not found")
    
    if review.provider_id != provider_id:
        raise HTTPException(status_code=403, detail="Only provider can reply")
    
    reply = crud.create_review_reply(db, review_id, provider_id, reply_in)
    
    # Notify review author
    crud.create_notification(
        db,
        user_id=review.user_id,
        notif_type=NotificationTypeEnum.PROVIDER_REPLY,
        title="Réponse du prestataire",
        message=f"{provider_id} a répondu à votre avis",
        payload={"review_id": review_id, "reply_id": reply.id}
    )
    
    return reply


@app.get("/api/reviews/{review_id}/replies", response_model=List[ReviewReplyOut], tags=["Replies"])
async def get_review_replies(review_id: str, db: Session = Depends(get_db)):
    """Get all replies for a review"""
    replies = crud.get_review_replies(db, review_id)
    return replies


# ============ REVIEW MODERATION (ADMIN) ============

@app.get("/api/admin/reviews/flagged", response_model=List[ReviewOut], tags=["Admin"])
async def get_flagged_reviews(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """Get all flagged reviews for moderation (admin endpoint)"""
    reviews = crud.get_flagged_reviews(db, skip, limit)
    return reviews


@app.patch("/api/admin/reviews/{review_id}/approve", response_model=ReviewOut, tags=["Admin"])
async def approve_review(
    review_id: str,
    admin_note: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """Approve a flagged review (admin only)"""
    review = crud.approve_flagged_review(db, review_id, admin_note)
    if not review:
        raise HTTPException(status_code=404, detail="Review not found")
    
    # Update statistics
    crud.update_provider_statistics(db, review.provider_id)
    
    # Notify provider
    crud.create_notification(
        db,
        user_id=review.provider_id,
        notif_type=NotificationTypeEnum.REVIEW_APPROVED,
        title="Avis approuvé",
        message=f"Un avis {review.rating}★ a été approuvé",
        provider_id=review.provider_id
    )
    
    return review


@app.patch("/api/admin/reviews/{review_id}/reject", response_model=ReviewOut, tags=["Admin"])
async def reject_review(
    review_id: str,
    admin_note: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """Reject and remove a flagged review (admin only)"""
    review = crud.reject_flagged_review(db, review_id, admin_note)
    if not review:
        raise HTTPException(status_code=404, detail="Review not found")
    
    # Notify review author
    crud.create_notification(
        db,
        user_id=review.user_id,
        notif_type=NotificationTypeEnum.REVIEW_REJECTED,
        title="Avis supprimé",
        message="Votre avis a été supprimé suite à modération",
        payload={"review_id": review_id}
    )
    
    return review


# ============ NOTIFICATIONS ============

@app.get("/api/notifications", response_model=List[NotificationOut], tags=["Notifications"])
async def get_notifications(
    user_id: Optional[str] = Query(None),
    provider_id: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """Get notifications for a user or provider"""
    if provider_id:
        return crud.get_provider_notifications(db, provider_id, skip, limit)
    elif user_id:
        return crud.get_user_notifications(db, user_id, skip, limit)
    else:
        raise HTTPException(status_code=400, detail="user_id or provider_id required")


@app.post("/api/notifications/{notification_id}/read", status_code=204, tags=["Notifications"])
async def mark_notification_read(notification_id: str, db: Session = Depends(get_db)):
    """Mark a notification as read"""
    result = crud.mark_notification_read(db, notification_id)
    if not result:
        raise HTTPException(status_code=404, detail="Notification not found")
    return None


@app.post("/api/notifications/mark-read", status_code=204, tags=["Notifications"])
async def mark_multiple_read(
    notification_ids: List[str],
    db: Session = Depends(get_db)
):
    """Mark multiple notifications as read"""
    crud.mark_notifications_read(db, notification_ids)
    return None


# ============ STATISTICS ============

@app.get("/api/reviews/stats/{provider_id}", response_model=dict, tags=["Statistics"])
async def get_provider_stats(provider_id: str, db: Session = Depends(get_db)):
    """Get review statistics for a provider"""
    stats = crud.get_provider_statistics(db, provider_id)
    
    if not stats:
        return {
            "provider_id": provider_id,
            "count": 0,
            "average_rating": 0.0,
            "rating_distribution": {
                "1": 0, "2": 0, "3": 0, "4": 0, "5": 0
            }
        }
    
    return {
        "provider_id": provider_id,
        "count": stats.total_reviews,
        "average_rating": round(stats.average_rating, 1),
        "rating_distribution": {
            "1": stats.rating_1_count,
            "2": stats.rating_2_count,
            "3": stats.rating_3_count,
            "4": stats.rating_4_count,
            "5": stats.rating_5_count,
        }
    }


# ============ INVITATIONS ============

@app.post("/api/invitations", response_model=ReviewInvitationOut, status_code=201, tags=["Invitations"])
async def create_invitation(
    invitation_in: ReviewInvitationCreate,
    db: Session = Depends(get_db)
):
    """Create a review invitation after order completion"""
    invitation = crud.create_review_invitation(db, invitation_in)
    
    # Send notification to user
    crud.create_notification(
        db,
        user_id=invitation_in.user_id,
        notif_type=NotificationTypeEnum.REVIEW_REMINDER,
        title="Partagez votre avis",
        message=f"Comment s'est déroulée votre prestation avec {invitation_in.provider_id}?",
        payload={"invitation_id": invitation.id, "order_id": invitation_in.order_id}
    )
    
    return invitation


@app.get("/api/invitations/pending", response_model=List[ReviewInvitationOut], tags=["Invitations"])
async def get_pending_invitations(user_id: str = Query(...), db: Session = Depends(get_db)):
    """Get pending review invitations for a user"""
    return crud.get_pending_invitations(db, user_id)


# ============ DEBUG/TESTING ENDPOINTS ============

@app.get("/api/debug/reviews-all/{provider_id}", tags=["Debug"])
async def debug_get_all_reviews(provider_id: str, db: Session = Depends(get_db)):
    """Debug: Get ALL reviews (including pending/flagged) for a provider"""
    reviews = crud.get_all_reviews_by_provider(db, provider_id)
    return [
        {
            "id": r.id,
            "rating": r.rating,
            "comment": r.comment,
            "status": r.status.value,
            "created_at": r.created_at
        }
        for r in reviews
    ]


@app.get("/api/debug/stats", tags=["Debug"])
async def debug_stats(db: Session = Depends(get_db)):
    """Debug: Get service stats"""
    return {
        "message": "Review service running",
        "database_url": os.getenv("DATABASE_URL", "not set"),
        "port": os.getenv("PORT", "8006")
    }


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8006))
    uvicorn.run(app, host="0.0.0.0", port=port)
