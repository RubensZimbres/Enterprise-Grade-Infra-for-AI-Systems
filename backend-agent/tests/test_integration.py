import pytest
from fastapi.testclient import TestClient
from main import app
from dependencies import get_current_user
from unittest.mock import patch

# This integration test mocks the external AI calls but tests the full FastAPI flow
# including dependency injection and router mounting.

@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c

def test_full_chat_flow(client):
    # 1. Health Check
    res = client.get("/health")
    assert res.status_code == 200
    assert res.json() == {"status": "healthy"}

    # 2. Chat without Auth (Should fail)
    # Clear any existing overrides first
    app.dependency_overrides = {}
    res = client.post("/chat", json={"session_id": "test-session", "message": "hello"})
    assert res.status_code in [401, 403]

    # 3. Chat with Mocked Auth and AI
    # Use dependency_overrides for Auth
    app.dependency_overrides[get_current_user] = lambda: {"uid": "test-user"}
    
    with patch("main.protected_chain_invoke", return_value="Integrated Response"):
        res = client.post("/chat", json={"session_id": "test-session", "message": "hello"})
        assert res.status_code == 200
        assert res.json()["response"] == "Integrated Response"

    # 4. Stream with Mocked Auth and AI
    async def mock_generator(message, session_id):
        yield "Streamed"
        yield "Response"

    with patch("main.protected_chain_stream", side_effect=mock_generator):
        res = client.post("/stream", json={"session_id": "test-session", "message": "hello"})
        assert res.status_code == 200
        assert b"StreamedResponse" in res.content
    
    # Clean up overrides
    app.dependency_overrides = {}
