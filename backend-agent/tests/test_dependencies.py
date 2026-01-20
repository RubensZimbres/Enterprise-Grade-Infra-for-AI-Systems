import pytest
from fastapi import HTTPException, Request
from unittest.mock import MagicMock, patch
from dependencies import get_current_user
from models import User

# Mock Request object
mock_request = MagicMock(spec=Request)

def test_get_current_user_missing_token(db_session):
    with pytest.raises(HTTPException) as exc:
        get_current_user(mock_request, x_firebase_token=None, db=db_session)
    assert exc.value.status_code == 401
    assert "Missing User Identity" in exc.value.detail

@patch("dependencies.auth.verify_id_token")
def test_get_current_user_invalid_token(mock_verify, db_session):
    mock_verify.side_effect = Exception("Invalid signature")
    
    with pytest.raises(HTTPException) as exc:
        get_current_user(mock_request, x_firebase_token="invalid-token", db=db_session)
    assert exc.value.status_code == 401
    assert "Invalid Token" in exc.value.detail

@patch("dependencies.auth.verify_id_token")
def test_get_current_user_no_email(mock_verify, db_session):
    mock_verify.return_value = {"uid": "123"} # No email in token
    
    with pytest.raises(HTTPException) as exc:
        get_current_user(mock_request, x_firebase_token="valid-token-no-email", db=db_session)
    assert exc.value.status_code == 401
    assert "Token missing email" in exc.value.detail

@patch("dependencies.auth.verify_id_token")
def test_get_current_user_not_in_db(mock_verify, db_session):
    mock_verify.return_value = {"email": "new@example.com"}
    # Database is empty for this user
    
    with pytest.raises(HTTPException) as exc:
        get_current_user(mock_request, x_firebase_token="valid-token", db=db_session)
    assert exc.value.status_code == 403
    assert "Payment Required" in exc.value.detail

@patch("dependencies.auth.verify_id_token")
def test_get_current_user_inactive(mock_verify, db_session):
    email = "inactive@example.com"
    mock_verify.return_value = {"email": email}
    
    # Create inactive user
    user = User(email=email, is_active=False)
    db_session.add(user)
    db_session.commit()
    
    with pytest.raises(HTTPException) as exc:
        get_current_user(mock_request, x_firebase_token="valid-token", db=db_session)
    assert exc.value.status_code == 403
    assert "Payment Required" in exc.value.detail

@patch("dependencies.auth.verify_id_token")
def test_get_current_user_success(mock_verify, db_session):
    email = "active@example.com"
    mock_verify.return_value = {"email": email}
    
    # Create active user
    user = User(email=email, is_active=True)
    db_session.add(user)
    db_session.commit()
    
    result_email = get_current_user(mock_request, x_firebase_token="valid-token", db=db_session)
    assert result_email == email
