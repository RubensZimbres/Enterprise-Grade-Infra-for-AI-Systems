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
        print(f"Warning: Could not fetch secret {secret_id}: {e}")
        return ""

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
    
    STRIPE_API_KEY: str = ""
    STRIPE_WEBHOOK_SECRET: str = ""
    
    # Computed
    DATABASE_URL: str = ""

    # App Config
    FIRESTORE_COLLECTION: str = "chat_history"
    DEBUG: str = "false"

    def load_secrets(self):
        if not self.PROJECT_ID:
            print("Warning: PROJECT_ID not set, skipping secret loading.")
            return

        # Fetch Configuration
        region_secret = get_secret(self.PROJECT_ID, "REGION")
        if region_secret: self.REGION = region_secret

        db_host_secret = get_secret(self.PROJECT_ID, "DB_HOST")
        if db_host_secret: self.DB_HOST = db_host_secret

        db_user_secret = get_secret(self.PROJECT_ID, "DB_USER")
        if db_user_secret: self.DB_USER = db_user_secret

        db_name_secret = get_secret(self.PROJECT_ID, "DB_NAME")
        if db_name_secret: self.DB_NAME = db_name_secret

        redis_host_secret = get_secret(self.PROJECT_ID, "REDIS_HOST")
        if redis_host_secret: self.REDIS_HOST = redis_host_secret

        # Fetch Secrets
        self.DB_PASSWORD = get_secret(self.PROJECT_ID, "DB_PASSWORD")
        self.STRIPE_API_KEY = get_secret(self.PROJECT_ID, "STRIPE_API_KEY")
        self.STRIPE_WEBHOOK_SECRET = get_secret(self.PROJECT_ID, "STRIPE_WEBHOOK_SECRET")
        
        # Try to fetch DATABASE_URL from secrets first
        db_url_secret = get_secret(self.PROJECT_ID, "DATABASE_URL")
        if db_url_secret:
            self.DATABASE_URL = db_url_secret
        else:
            # Fallback: construct it
            if self.DB_HOST and self.DB_PASSWORD:
                 self.DATABASE_URL = f"postgresql://{quote_plus(self.DB_USER)}:{quote_plus(self.DB_PASSWORD)}@{self.DB_HOST}:5432/{self.DB_NAME}"
            else:
                 self.DATABASE_URL = "postgresql://user:password@localhost/dbname" 

    class Config:
        # No env_file for production as secrets are injected as env vars
        pass

settings = Settings()
settings.load_secrets()