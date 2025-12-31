from fastapi import Header, HTTPException, Depends, Request
import firebase_admin
from firebase_admin import auth, credentials
import logging
from sqlalchemy.orm import Session
from database import get_db
import crud
from config import settings

logger = logging.getLogger(__name__)

# Initialize Firebase Admin SDK
# Use Application Default Credentials (ADC) which works automatically on Cloud Run
try:
    firebase_admin.get_app()
except ValueError:
    firebase_admin.initialize_app()

def get_current_user(request: Request, x_firebase_token: str = Header(None, alias="X-Firebase-Token"), db: Session = Depends(get_db)):
    """
    Validates the Firebase User Identity passed from the Frontend AND checks DB subscription status.
    """
    # 0. LOCAL DEVELOPMENT FALLBACK
    # If we are in local development and have a mock token, bypass Firebase Auth
    if settings.DEBUG.lower() == "true":
        # Removed insecure backdoor
        pass

    # 1. Verify Firebase Token
    if not x_firebase_token:
        logger.warning("Missing X-Firebase-Token header")
        raise HTTPException(status_code=401, detail="Unauthorized: Missing User Identity")

    try:
        # Verify the ID token while checking if the token is revoked.
        decoded_token = auth.verify_id_token(x_firebase_token, check_revoked=True)
        user_email = decoded_token.get("email")
        
        if not user_email:
             # If using providers like GitHub/Twitter, email might be missing or not verified.
             # For this app, we strictly require an email for the session scope.
             raise HTTPException(status_code=401, detail="Unauthorized: Token missing email")
             
        # 2. Check Database for Active Subscription
        db_user = crud.get_user(db, user_email)
        if not db_user or not db_user.is_active:
            logger.warning(f"User {user_email} attempted access without active subscription.")
            raise HTTPException(status_code=403, detail="Payment Required: Active subscription needed.")

        return user_email

    except auth.RevokedIdTokenError:
        logger.warning("Firebase token revoked")
        raise HTTPException(status_code=401, detail="Unauthorized: Token Revoked")
    except auth.ExpiredIdTokenError:
        logger.warning("Firebase token expired")
        raise HTTPException(status_code=401, detail="Unauthorized: Token Expired")
    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"Firebase token validation error: {e}")
        raise HTTPException(status_code=401, detail="Unauthorized: Invalid Token")