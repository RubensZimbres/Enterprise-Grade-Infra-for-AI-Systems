import pytest
from crud import create_user, get_user, update_user_subscription
from models import User

def test_create_user(db_session):
    email = "test@example.com"
    user = create_user(db_session, email=email)
    
    assert user.email == email
    assert user.is_active is False
    assert user.subscription_status == "inactive"
    
    fetched_user = get_user(db_session, email)
    assert fetched_user is not None
    assert fetched_user.email == email

def test_update_user_subscription(db_session):
    email = "sub@example.com"
    # Should create if not exists
    user = update_user_subscription(db_session, email, "active", "cus_123")
    
    assert user.subscription_status == "active"
    assert user.is_active is True
    assert user.stripe_customer_id == "cus_123"
    
    # Update existing
    updated_user = update_user_subscription(db_session, email, "canceled")
    assert updated_user.subscription_status == "canceled"
    assert updated_user.is_active is False
    # Stripe ID should persist
    assert updated_user.stripe_customer_id == "cus_123"

def test_get_nonexistent_user(db_session):
    user = get_user(db_session, "fake@example.com")
    assert user is None
