import pytest
from unittest.mock import patch
from sqlalchemy.exc import SQLAlchemyError
from crud import (
    create_user,
    get_user,
    update_user_subscription,
    update_subscription_by_stripe_id,
)


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


def test_update_subscription_by_stripe_id(db_session):
    # Test updating non-existent user
    non_existent = update_subscription_by_stripe_id(db_session, "cus_fake", "active")
    assert non_existent is None

    # Create a user first
    email = "stripe@example.com"
    create_user(db_session, email, "cus_real")

    # Test updating existing user to active
    user = update_subscription_by_stripe_id(db_session, "cus_real", "active")
    assert user is not None
    assert user.subscription_status == "active"
    assert user.is_active is True

    # Test updating existing user to canceled
    user = update_subscription_by_stripe_id(db_session, "cus_real", "canceled")
    assert user is not None
    assert user.subscription_status == "canceled"
    assert user.is_active is False


def test_update_subscription_by_stripe_id_error(db_session):
    with patch("crud.logger") as mock_logger:
        with patch.object(db_session, "rollback") as mock_rollback:
            with patch.object(db_session, "query") as mock_query:
                # Simulate a SQLAlchemyError when querying the database
                mock_query.side_effect = SQLAlchemyError("Database error")

                with pytest.raises(SQLAlchemyError) as exc_info:
                    update_subscription_by_stripe_id(db_session, "cus_error", "active")

                assert "Database error" in str(exc_info.value)
                mock_logger.error.assert_called_once_with(
                    "Error updating subscription for stripe_id cus_error: Database error"
                )
                mock_rollback.assert_called_once()
