import pytest
import os
from config import Settings

def test_settings_explicit_database_url():
    settings = Settings(
        DATABASE_URL="postgresql://custom:custom@custom:5432/custom",
        DEBUG="true"
    )
    assert settings.DATABASE_URL == "postgresql://custom:custom@custom:5432/custom"

def test_settings_construct_database_url(monkeypatch):
    # Temporarily remove DATABASE_URL from environment for this test
    # so the fallback/construction logic in Settings can actually run.
    monkeypatch.delenv("DATABASE_URL", raising=False)

    settings = Settings(
        DATABASE_URL="",
        DB_HOST="dbhost",
        DB_PASSWORD="dbpass@word!",
        DB_USER="dbuser",
        DB_NAME="dbname",
        DEBUG="true"
    )
    assert settings.DATABASE_URL == "postgresql://dbuser:dbpass%40word%21@dbhost:5432/dbname"

def test_settings_fallback_database_url(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    settings = Settings(
        DEBUG="true",
        DATABASE_URL="",
        DB_HOST="",
        DB_PASSWORD=""
    )
    assert settings.DATABASE_URL == "postgresql://user:password@localhost/dbname"

def test_settings_production_missing_secrets():
    with pytest.raises(ValueError) as exc_info:
        Settings(
            DEBUG="false",
            STRIPE_API_KEY="",
            STRIPE_WEBHOOK_SECRET="",
            REDIS_PASSWORD=""
        )
    assert "CRITICAL: Missing production secrets" in str(exc_info.value)
    assert "STRIPE_API_KEY" in str(exc_info.value)
    assert "STRIPE_WEBHOOK_SECRET" in str(exc_info.value)
    assert "REDIS_PASSWORD" in str(exc_info.value)

def test_settings_production_has_secrets():
    settings = Settings(
        DEBUG="false",
        STRIPE_API_KEY="sk_test_123",
        STRIPE_WEBHOOK_SECRET="whsec_123",
        REDIS_PASSWORD="redispass"
    )
    assert settings.STRIPE_API_KEY == "sk_test_123"

def test_settings_debug_missing_secrets():
    settings = Settings(
        DEBUG="true",
        STRIPE_API_KEY="",
        STRIPE_WEBHOOK_SECRET="",
        REDIS_PASSWORD=""
    )
    assert settings.DEBUG == "true"
