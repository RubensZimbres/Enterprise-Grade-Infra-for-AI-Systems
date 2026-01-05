import os
from urllib.parse import quote_plus
from google.cloud import secretmanager
from pydantic_settings import BaseSettings

def get_secret(project_id: str, secret_id: str, version_id: str = "1") -> str:
    try:
        client = secretmanager.SecretManagerServiceClient()
        name = f"projects/{project_id}/secrets/{secret_id}/versions/{version_id}"
        response = client.access_secret_version(request={"name": name})
        return response.payload.data.decode('UTF-8')
    except Exception as e:
        # FAIL FAST: If a required secret is missing, the app should not start.
        print(f"CRITICAL: Could not fetch secret {secret_id}: {e}")
        raise e

class Settings(BaseSettings):
    # Bootstrapping Variable (Must remain in Env)
    PROJECT_ID: str

    # Configuration & Secrets (Loaded from Secret Manager)
    REGION: str = "us-central1" # Default fallback, will try to load
    DB_HOST: str = ""
    DB_USER: str = "postgres"
    DB_PASSWORD: str = ""
    DB_NAME: str = "postgres"

    REDIS_HOST: str = "localhost"
    REDIS_PASSWORD: str = ""

    STRIPE_API_KEY: str = ""
    STRIPE_WEBHOOK_SECRET: str = ""

    # Computed
    DATABASE_URL: str = ""

    # App Config
    FIRESTORE_COLLECTION: str = "chat_history"
    DEBUG: str = "false"

    # CORS Configuration
    FRONTEND_URL: str = "http://localhost:3000"

    def load_secrets(self):
        if not self.PROJECT_ID:
            print("Warning: PROJECT_ID not set, skipping secret loading.")
            return

        # Fetch Configuration
        try:
            region_secret = get_secret(self.PROJECT_ID, "REGION")
            if region_secret: self.REGION = region_secret

            # Allow overriding FRONTEND_URL via Secret
            frontend_url_secret = get_secret(self.PROJECT_ID, "FRONTEND_URL")
            if frontend_url_secret: self.FRONTEND_URL = frontend_url_secret
        except:
            # Non-critical secrets can be skipped if you prefer,
            # but generally we want to fail if infrastructure implies they exist.
            pass

        try:
            db_host_secret = get_secret(self.PROJECT_ID, "DB_HOST")
            if db_host_secret: self.DB_HOST = db_host_secret
        except Exception as e:
            print(f"Warning: Could not fetch DB_HOST from secrets: {e}")

        try:
            db_user_secret = get_secret(self.PROJECT_ID, "DB_USER")
            if db_user_secret: self.DB_USER = db_user_secret
        except Exception as e:
             print(f"Warning: Could not fetch DB_USER from secrets: {e}")

        try:
            db_name_secret = get_secret(self.PROJECT_ID, "DB_NAME")
            if db_name_secret: self.DB_NAME = db_name_secret
        except Exception as e:
             print(f"Warning: Could not fetch DB_NAME from secrets: {e}")

        try:
            redis_host_secret = get_secret(self.PROJECT_ID, "REDIS_HOST")
            if redis_host_secret: self.REDIS_HOST = redis_host_secret
        except Exception as e:
             print(f"Warning: Could not fetch REDIS_HOST from secrets: {e}")

        try:
            redis_password_secret = get_secret(self.PROJECT_ID, "REDIS_PASSWORD")
            if redis_password_secret: self.REDIS_PASSWORD = redis_password_secret
        except Exception as e:
             print(f"Warning: Could not fetch REDIS_PASSWORD from secrets: {e}")

        # Fetch Secrets
        try:
            self.DB_PASSWORD = get_secret(self.PROJECT_ID, "DB_PASSWORD")
        except Exception as e:
             print(f"Warning: Could not fetch DB_PASSWORD from secrets: {e}")

        try:
            self.STRIPE_API_KEY = get_secret(self.PROJECT_ID, "STRIPE_API_KEY")
        except Exception as e:
             print(f"Warning: Could not fetch STRIPE_API_KEY from secrets: {e}")

        try:
            self.STRIPE_WEBHOOK_SECRET = get_secret(self.PROJECT_ID, "STRIPE_WEBHOOK_SECRET")
        except Exception as e:
             print(f"Warning: Could not fetch STRIPE_WEBHOOK_SECRET from secrets: {e}")

        # Try to fetch DATABASE_URL from secrets first
        try:
            db_url_secret = get_secret(self.PROJECT_ID, "DATABASE_URL")
            if db_url_secret:
                self.DATABASE_URL = db_url_secret
        except Exception as e:
             print(f"Warning: Could not fetch DATABASE_URL from secrets: {e}")

        if not self.DATABASE_URL:
            # Fallback: construct it
            if self.DB_HOST and self.DB_PASSWORD:
                 self.DATABASE_URL = f"postgresql://{quote_plus(self.DB_USER)}:{quote_plus(self.DB_PASSWORD)}@{self.DB_HOST}:5432/{self.DB_NAME}"
            else:
                 self.DATABASE_URL = "postgresql://user:password@localhost/dbname"

    class Config:
        # Load .env file for local development
        env_file = ".env"
        env_file_encoding = "utf-8"

settings = Settings()
settings.load_secrets()