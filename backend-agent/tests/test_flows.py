import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from fastapi.testclient import TestClient
from main import app
from ingest import ingest_data
from models import User
from dependencies import get_current_user

@pytest.fixture
def client():
    return TestClient(app)

@pytest.fixture
def mock_db_session():
    return MagicMock()

# --- Ingest Flow Tests ---

@pytest.mark.asyncio
@patch("ingest.DirectoryLoader")
@patch("ingest.RecursiveCharacterTextSplitter")
@patch("ingest.VertexAIEmbeddings")
@patch("ingest.PGVector")
async def test_ingest_flow(mock_pgvector, mock_embeddings, mock_splitter, mock_loader):
    # Mock DirectoryLoader to return some documents
    mock_loader_instance = mock_loader.return_value
    mock_loader_instance.load.return_value = [
        MagicMock(page_content="Test content", metadata={"source": "test.pdf"})
    ]

    # Mock TextSplitter
    mock_splitter_instance = mock_splitter.return_value
    mock_splitter_instance.split_documents.return_value = [
        MagicMock(page_content="Test content chunk", metadata={"source": "test.pdf"})
    ]

    # Mock PGVector
    mock_vector_store = mock_pgvector.return_value
    mock_vector_store.add_documents = AsyncMock()

    # Run Ingest
    # We need to mock os.path.exists to return True for DATA_PATH check
    with patch("os.path.exists", return_value=True):
        await ingest_data()

    # Verify loader was called
    mock_loader.assert_called()
    mock_loader_instance.load.assert_called()

    # Verify splitter was called
    mock_splitter.assert_called()
    mock_splitter_instance.split_documents.assert_called()

    # Verify vector store add_documents was called
    mock_vector_store.add_documents.assert_called()


# --- Chat Flow with Permissions Tests ---

@patch("main.protected_graph_invoke")
@patch("dependencies.auth.verify_id_token")
@patch("dependencies.crud.get_user")
def test_chat_flow_active_user(mock_get_user, mock_verify, mock_chain, client, mock_db_session):
    # 1. Setup Active User
    mock_verify.return_value = {"email": "active@example.com", "uid": "123"}
    mock_user = User(email="active@example.com", is_active=True)
    mock_get_user.return_value = mock_user
    
    mock_chain.return_value = "AI Response"

    # 2. Make Request
    # Note: We don't need to override get_current_user here because we are mocking the internals
    # of dependencies.auth and crud.get_user which get_current_user calls.
    # However, `get_db` dependency needs to yield our mock session if we want strict control,
    # but `crud.get_user` mock is enough if we trust the dependency injection of the session.
    # Actually, main.py uses `get_current_user` which calls `get_db`.
    # To use our mocks inside `get_current_user`, we rely on `patch` working globally.
    
    response = client.post(
        "/chat", 
        json={"session_id": "123", "message": "hello"},
        headers={"Authorization": "Bearer valid-token", "X-Firebase-Token": "valid-token"}
    )
    
    assert response.status_code == 200
    assert response.json()["response"] == "AI Response"

@patch("dependencies.auth.verify_id_token")
@patch("dependencies.crud.get_user")
def test_chat_flow_inactive_user(mock_get_user, mock_verify, client):
    # 1. Setup Inactive User
    mock_verify.return_value = {"email": "inactive@example.com", "uid": "456"}
    mock_user = User(email="inactive@example.com", is_active=False)
    mock_get_user.return_value = mock_user

    # 2. Make Request
    response = client.post(
        "/chat", 
        json={"session_id": "123", "message": "hello"},
        headers={"Authorization": "Bearer valid-token", "X-Firebase-Token": "valid-token"}
    )
    
    assert response.status_code == 403
    assert "Payment Required" in response.json()["detail"]

@patch("dependencies.auth.verify_id_token")
def test_chat_flow_invalid_token(mock_verify, client):
    # 1. Setup Invalid Token
    mock_verify.side_effect = Exception("Invalid token")

    # 2. Make Request
    response = client.post(
        "/chat", 
        json={"session_id": "123", "message": "hello"},
        headers={"Authorization": "Bearer invalid-token", "X-Firebase-Token": "invalid-token"}
    )
    
    assert response.status_code == 401
