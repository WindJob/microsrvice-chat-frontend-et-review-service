from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, timedelta
from models import (
    Review, ReviewReply, ReviewFlag, Notification, 
    ReviewStatistics, ReviewInvitation, ReviewStatusEnum, NotificationTypeEnum
)
from schemas import (
    ReviewCreate, ReviewUpdate, ReviewReplyCreate, 
    ReviewFlagCreate, ReviewInvitationCreate
)
import uuid


# ============ REVIEW CRUD ============

def create_review(db: Session, review_in: ReviewCreate) -> Review:
    """Create a new review"""
    review = Review(
        id=str(uuid.uuid4()),
        order_id=review_in.order_id,
        provider_id=review_in.provider_id,
        user_id=review_in.user_id,
        rating=review_in.rating,
        comment=review_in.comment,
        status=ReviewStatusEnum.PENDING,
        edited_until=datetime.utcnow() + timedelta(hours=72)
    )
    db.add(review)
    db.commit()
    db.refresh(review)
    return review


def get_review(db: Session, review_id: str) -> Review:
    """Get a single review by ID"""
    return db.query(Review).filter(Review.id == review_id).first()


def get_reviews_by_provider(db: Session, provider_id: str, skip: int = 0, limit: int = 50) -> list:
    """Get all approved reviews for a provider"""
    return (
        db.query(Review)
        .filter(Review.provider_id == provider_id, Review.status == ReviewStatusEnum.APPROVED)
        .order_by(Review.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )


def get_all_reviews_by_provider(db: Session, provider_id: str, skip: int = 0, limit: int = 50) -> list:
    """Get all reviews (including pending) for a provider"""
    return (
        db.query(Review)
        .filter(Review.provider_id == provider_id)
        .order_by(Review.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )


def update_review(db: Session, review_id: str, review_update: ReviewUpdate) -> Review:
    """Update a review (only if within edit window)"""
    review = get_review(db, review_id)
    if not review:
        return None
    
    if review.edited_until and datetime.utcnow() > review.edited_until:
        return None  # Edit window closed
    
    if review_update.rating:
        review.rating = review_update.rating
    if review_update.comment:
        review.comment = review_update.comment
    
    review.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(review)
    return review


def delete_review(db: Session, review_id: str) -> bool:
    """Delete a review"""
    review = get_review(db, review_id)
    if not review:
        return False
    db.delete(review)
    db.commit()
    return True


def get_review_by_order(db: Session, order_id: str) -> Review:
    """Get review by order ID (one review per order)"""
    return db.query(Review).filter(Review.order_id == order_id).first()


# ============ REVIEW REPLY CRUD ============

def create_review_reply(db: Session, review_id: str, provider_id: str, reply_in: ReviewReplyCreate) -> ReviewReply:
    """Add a reply from provider to a review"""
    reply = ReviewReply(
        id=str(uuid.uuid4()),
        review_id=review_id,
        provider_id=provider_id,
        text=reply_in.text
    )
    db.add(reply)
    db.commit()
    db.refresh(reply)
    return reply


def get_review_replies(db: Session, review_id: str) -> list:
    """Get all replies for a review"""
    return db.query(ReviewReply).filter(ReviewReply.review_id == review_id).all()


# ============ REVIEW FLAG CRUD ============

def create_review_flag(db: Session, review_id: str, flag_in: ReviewFlagCreate) -> ReviewFlag:
    """Flag a review for moderation"""
    flag = ReviewFlag(
        id=str(uuid.uuid4()),
        review_id=review_id,
        reason=flag_in.reason,
        reporter_id=flag_in.reporter_id,
        status="pending"
    )
    db.add(flag)
    
    # Auto-flag the review
    review = get_review(db, review_id)
    if review:
        review.status = ReviewStatusEnum.FLAGGED
    
    db.commit()
    db.refresh(flag)
    return flag


def get_flagged_reviews(db: Session, skip: int = 0, limit: int = 50) -> list:
    """Get all flagged reviews for admin moderation"""
    return (
        db.query(Review)
        .filter(Review.status == ReviewStatusEnum.FLAGGED)
        .order_by(Review.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )


def approve_flagged_review(db: Session, review_id: str, admin_note: str = None) -> Review:
    """Approve a flagged review"""
    review = get_review(db, review_id)
    if not review:
        return None
    
    review.status = ReviewStatusEnum.APPROVED
    
    # Update flag
    flag = db.query(ReviewFlag).filter(ReviewFlag.review_id == review_id).first()
    if flag:
        flag.status = "reviewed"
        flag.admin_note = admin_note
    
    db.commit()
    db.refresh(review)
    return review


def reject_flagged_review(db: Session, review_id: str, admin_note: str = None) -> Review:
    """Reject a flagged review"""
    review = get_review(db, review_id)
    if not review:
        return None
    
    review.status = ReviewStatusEnum.REJECTED
    
    # Update flag
    flag = db.query(ReviewFlag).filter(ReviewFlag.review_id == review_id).first()
    if flag:
        flag.status = "reviewed"
        flag.admin_note = admin_note
    
    db.commit()
    db.refresh(review)
    return review


# ============ NOTIFICATION CRUD ============

def create_notification(
    db: Session,
    user_id: str,
    notif_type: NotificationTypeEnum,
    title: str,
    message: str,
    provider_id: str = None,
    payload: dict = None
) -> Notification:
    """Create a notification"""
    notification = Notification(
        id=str(uuid.uuid4()),
        user_id=user_id,
        provider_id=provider_id,
        type=notif_type,
        title=title,
        message=message,
        payload=payload,
        status="unread"
    )
    db.add(notification)
    db.commit()
    db.refresh(notification)
    return notification


def get_user_notifications(db: Session, user_id: str, skip: int = 0, limit: int = 50) -> list:
    """Get all notifications for a user"""
    return (
        db.query(Notification)
        .filter(Notification.user_id == user_id)
        .order_by(Notification.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )


def get_provider_notifications(db: Session, provider_id: str, skip: int = 0, limit: int = 50) -> list:
    """Get all notifications for a provider"""
    return (
        db.query(Notification)
        .filter(Notification.provider_id == provider_id)
        .order_by(Notification.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )


def mark_notification_read(db: Session, notification_id: str) -> Notification:
    """Mark a notification as read"""
    notif = db.query(Notification).filter(Notification.id == notification_id).first()
    if not notif:
        return None
    notif.status = "read"
    notif.read_at = datetime.utcnow()
    db.commit()
    db.refresh(notif)
    return notif


def mark_notifications_read(db: Session, notification_ids: list) -> int:
    """Mark multiple notifications as read"""
    count = db.query(Notification).filter(Notification.id.in_(notification_ids)).update(
        {Notification.status: "read", Notification.read_at: datetime.utcnow()}
    )
    db.commit()
    return count


# ============ STATISTICS CRUD ============

def update_provider_statistics(db: Session, provider_id: str) -> ReviewStatistics:
    """Update statistics for a provider"""
    stats = db.query(ReviewStatistics).filter(ReviewStatistics.provider_id == provider_id).first()
    
    reviews = db.query(Review).filter(
        Review.provider_id == provider_id,
        Review.status == ReviewStatusEnum.APPROVED
    ).all()
    
    if not stats:
        stats = ReviewStatistics(
            id=str(uuid.uuid4()),
            provider_id=provider_id
        )
        db.add(stats)
    
    stats.total_reviews = len(reviews)
    
    # Calculate ratings
    ratings = [r.rating for r in reviews]
    stats.average_rating = sum(ratings) / len(ratings) if ratings else 0.0
    
    # Count by rating
    stats.rating_1_count = sum(1 for r in ratings if r == 1)
    stats.rating_2_count = sum(1 for r in ratings if r == 2)
    stats.rating_3_count = sum(1 for r in ratings if r == 3)
    stats.rating_4_count = sum(1 for r in ratings if r == 4)
    stats.rating_5_count = sum(1 for r in ratings if r == 5)
    stats.last_updated = datetime.utcnow()
    
    db.commit()
    db.refresh(stats)
    return stats


def get_provider_statistics(db: Session, provider_id: str) -> ReviewStatistics:
    """Get statistics for a provider"""
    return db.query(ReviewStatistics).filter(ReviewStatistics.provider_id == provider_id).first()


# ============ INVITATION CRUD ============

def create_review_invitation(db: Session, invitation_in: ReviewInvitationCreate) -> ReviewInvitation:
    """Create a review invitation after order completion"""
    invitation = ReviewInvitation(
        id=str(uuid.uuid4()),
        order_id=invitation_in.order_id,
        provider_id=invitation_in.provider_id,
        user_id=invitation_in.user_id,
        status="pending",
        expires_at=datetime.utcnow() + timedelta(days=30)
    )
    db.add(invitation)
    db.commit()
    db.refresh(invitation)
    return invitation


def get_pending_invitations(db: Session, user_id: str) -> list:
    """Get all pending invitations for a user"""
    return (
        db.query(ReviewInvitation)
        .filter(ReviewInvitation.user_id == user_id, ReviewInvitation.status == "pending")
        .filter(ReviewInvitation.expires_at > datetime.utcnow())
        .all()
    )


def complete_invitation(db: Session, order_id: str) -> ReviewInvitation:
    """Mark invitation as completed when review is submitted"""
    invitation = db.query(ReviewInvitation).filter(ReviewInvitation.order_id == order_id).first()
    if invitation:
        invitation.status = "completed"
        db.commit()
        db.refresh(invitation)
    return invitation


def expire_old_invitations(db: Session) -> int:
    """Expire old invitations (scheduled job)"""
    count = db.query(ReviewInvitation).filter(
        ReviewInvitation.status == "pending",
        ReviewInvitation.expires_at < datetime.utcnow()
    ).update({ReviewInvitation.status: "expired"})
    db.commit()
    return count
