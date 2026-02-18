import os
import sys
from unittest.mock import MagicMock

# 1. Set required environment variables for testing
os.environ["PROJECT_ID"] = "test-project"
os.environ["REGION"] = "us-central1"
os.environ["DATABASE_URL"] = "sqlite:///./test.db"

# 2. Mock Google Cloud Secret Manager to avoid network calls during config import
mock_secret_manager = MagicMock()
mock_client = MagicMock()


def access_secret_side_effect(request=None, **kwargs):
    name = request.get("name", "")
    # name format: projects/{project}/secrets/{secret}/versions/{version}
    try:
        secret_id = name.split("/secrets/")[1].split("/")[0]
    except IndexError:
        secret_id = "UNKNOWN"

    mock_res = MagicMock()
    if secret_id == "REGION":
        mock_res.payload.data.decode.return_value = "us-central1"
    elif secret_id == "DATABASE_URL":
        # Use an in-memory sqlite db for tests if possible, or a valid connection string structure
        mock_res.payload.data.decode.return_value = "sqlite:///./test.db"
    elif secret_id == "DB_HOST":
        mock_res.payload.data.decode.return_value = "localhost"
    elif secret_id == "DB_USER":
        mock_res.payload.data.decode.return_value = "user"
    elif secret_id == "DB_PASSWORD":
        mock_res.payload.data.decode.return_value = "pass"
    elif secret_id == "DB_NAME":
        mock_res.payload.data.decode.return_value = "db"
    elif secret_id == "REDIS_HOST":
        mock_res.payload.data.decode.return_value = "localhost"
    else:
        mock_res.payload.data.decode.return_value = "mock-secret"
    return mock_res


mock_client.access_secret_version.side_effect = access_secret_side_effect
mock_secret_manager.SecretManagerServiceClient.return_value = mock_client
sys.modules["google.cloud.secretmanager"] = mock_secret_manager

# 3. Mock LangChain integrations to avoid init-time validation/network calls
sys.modules["langchain_google_vertexai"] = MagicMock()
sys.modules["langchain_postgres"] = MagicMock()
sys.modules["langchain_google_firestore"] = MagicMock()
sys.modules["langchain_redis"] = MagicMock()
sys.modules["redis"] = MagicMock()

# 4. Mock cache_manager to avoid GenAI calls
mock_cache_manager_module = MagicMock()
mock_cache_manager_instance = MagicMock()
mock_cache_manager_instance.get_or_create_cache.return_value = (
    "projects/test/locations/us-central1/cachedContents/123"
)
mock_cache_manager_module.cache_manager = mock_cache_manager_instance
# Also need to mock SYSTEM_INSTRUCTION_TEXT as it is imported
mock_cache_manager_module.SYSTEM_INSTRUCTION_TEXT = "System prompt"
sys.modules["cache_manager"] = mock_cache_manager_module

# 5. Mock DLP Client
sys.modules["google.cloud.dlp_v2"] = MagicMock()

# 6. Mock OpenTelemetry to avoid import errors and side effects
sys.modules["opentelemetry"] = MagicMock()
sys.modules["opentelemetry.exporter"] = MagicMock()
sys.modules["opentelemetry.exporter.cloud_trace"] = MagicMock()
sys.modules["opentelemetry.instrumentation"] = MagicMock()
sys.modules["opentelemetry.instrumentation.fastapi"] = MagicMock()
sys.modules["opentelemetry.instrumentation.langchain"] = MagicMock()
sys.modules["opentelemetry.propagate"] = MagicMock()
sys.modules["opentelemetry.propagators"] = MagicMock()
sys.modules["opentelemetry.propagators.cloud_trace_propagator"] = MagicMock()
sys.modules["opentelemetry.sdk"] = MagicMock()
sys.modules["opentelemetry.sdk.trace"] = MagicMock()
sys.modules["opentelemetry.sdk.trace.export"] = MagicMock()

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

# Import main AFTER setting up mocks
from main import app  # noqa: E402
from dependencies import get_current_user  # noqa: E402


@pytest.fixture
def client():
    # Override dependencies if needed (e.g. auth)
    # For now, we return a simple client.
    # Mocks can be applied in specific tests or here as needed.
    with TestClient(app) as c:
        yield c


@pytest.fixture
def mock_auth_user(client):
    """
    Overrides the get_current_user dependency to bypass auth.
    """
    app.dependency_overrides[get_current_user] = lambda: "test@example.com"
    yield
    app.dependency_overrides = {}


@pytest.fixture
def db_session():
    """
    Creates a new database session for a test.
    """
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from database import Base

    # Use in-memory SQLite for testing
    SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"
    engine = create_engine(
        SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
    )
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    Base.metadata.create_all(bind=engine)

    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
