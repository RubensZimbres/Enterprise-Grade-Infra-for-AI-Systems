from sqlalchemy.orm import Session
from models import User
import logging

logger = logging.getLogger(__name__)

def get_user(db: Session, email: str):
    return db.query(User).filter(User.email == email).first()

def create_user(db: Session, email: str, stripe_customer_id: str = None):
    db_user = User(email=email, stripe_customer_id=stripe_customer_id, is_active=False)
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

def update_user_subscription(db: Session, email: str, status: str, stripe_customer_id: str = None):
    user = get_user(db, email)
    if not user:
        user = create_user(db, email, stripe_customer_id)
    
    user.subscription_status = status
    user.is_active = status == 'active'
    if stripe_customer_id:
        user.stripe_customer_id = stripe_customer_id
        
    db.commit()
    db.refresh(user)
    return user
