from urllib.parse import quote_plus
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # These will be populated by:
    # 1. Cloud Run "Secret Injection" (Production)
    # 2. Local .env file (Development)
    PROJECT_ID: str = "local-project"  # Default for local dev if not set
    REGION: str = "us-central1"

    # Secrets
    DB_PASSWORD: str = ""
    STRIPE_API_KEY: str = ""
    STRIPE_WEBHOOK_SECRET: str = ""

    # Config
    DB_HOST: str = ""
    DB_USER: str = "postgres"
    DB_NAME: str = "postgres"
    REDIS_HOST: str = "localhost"
    REDIS_PASSWORD: str = ""

    # Computed
    DATABASE_URL: str = ""

    # App Config
    FIRESTORE_COLLECTION: str = "chat_history"
    DEBUG: str = "false"

    # CORS Configuration
    FRONTEND_URL: str = "http://localhost:3000"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        # Construct Database URL if not provided explicitly
        if not self.DATABASE_URL and self.DB_HOST and self.DB_PASSWORD:
            self.DATABASE_URL = f"postgresql://{quote_plus(self.DB_USER)}:{quote_plus(self.DB_PASSWORD)}@{self.DB_HOST}:5432/{self.DB_NAME}"

        # Fallback for local development if no DB credentials present yet
        if not self.DATABASE_URL:
            self.DATABASE_URL = "postgresql://user:password@localhost/dbname"

        # Production Validation
        if self.DEBUG.lower() != "true":
            missing_secrets = []
            if not self.STRIPE_API_KEY:
                missing_secrets.append("STRIPE_API_KEY")
            if not self.STRIPE_WEBHOOK_SECRET:
                missing_secrets.append("STRIPE_WEBHOOK_SECRET")
            if not self.REDIS_PASSWORD:
                missing_secrets.append("REDIS_PASSWORD")
            
            if missing_secrets:
                raise ValueError(f"CRITICAL: Missing production secrets: {', '.join(missing_secrets)}")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"


settings = Settings()
