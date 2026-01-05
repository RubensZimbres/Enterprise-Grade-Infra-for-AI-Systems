import pytest
from unittest.mock import AsyncMock, MagicMock
from fastapi import HTTPException

def test_health_check(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}

def test_chat_endpoint_auth_required(client):
    # Without auth override, this should fail (assuming the real dependency checks a token)
    response = client.post("/chat", json={"session_id": "123", "message": "hello"})
    assert response.status_code in [401, 403]

def test_chat_endpoint_success(client, mock_auth_user, mocker):
    # Mock the protected_chain_invoke to avoid hitting Vertex AI
    mocker.patch("main.protected_chain_invoke", return_value="Hello from Mock AI")

    response = client.post("/chat", json={"session_id": "123", "message": "hello"})
    assert response.status_code == 200
    assert response.json() == {"response": "Hello from Mock AI"}

def test_chat_endpoint_token_limit(client, mock_auth_user, mocker):
    # Mock validate_token_count to raise HTTPException
    mocker.patch("main.validate_token_count", side_effect=HTTPException(status_code=400, detail="Message too long"))

    response = client.post("/chat", json={"session_id": "123", "message": "A very long message..."})
    assert response.status_code == 400
    assert response.json() == {"detail": "Message too long"}

def test_chat_endpoint_internal_error(client, mock_auth_user, mocker):
    # Mock protected_chain_invoke to raise an exception
    mocker.patch("main.protected_chain_invoke", side_effect=Exception("Something went wrong"))

    response = client.post("/chat", json={"session_id": "123", "message": "hello"})
    assert response.status_code == 500
    assert response.json() == {"detail": "Internal Processing Error"}

def test_stream_endpoint_success(client, mock_auth_user, mocker):
    # Mock protected_chain_stream to return an async generator
    async def mock_stream_generator(message, session_id):
        yield "Hello "
        yield "from "
        yield "Stream"

    mocker.patch("main.protected_chain_stream", side_effect=mock_stream_generator)

    response = client.post("/stream", json={"session_id": "123", "message": "hello"})
    assert response.status_code == 200
    # StreamingResponse returns content in chunks. TestClient streams it.
    assert b"Hello from Stream" in response.content

def test_stream_endpoint_error(client, mock_auth_user, mocker):
    # Mock protected_chain_stream to raise an exception immediately
    mocker.patch("main.protected_chain_stream", side_effect=Exception("Stream failed"))

    response = client.post("/stream", json={"session_id": "123", "message": "hello"})
    # Note: If an error occurs during streaming setup, FastAPI returns 500.
    assert response.status_code == 500
    assert response.json() == {"detail": "Streaming Error"}
