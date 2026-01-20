import pytest
from unittest.mock import MagicMock, patch, AsyncMock
import main

# Mock Cloud Event
class MockCloudEvent:
    def __init__(self, data):
        self.data = data
        self._attributes = {"id": "123", "type": "google.cloud.storage.object.v1.finalized"}
    
    def __getitem__(self, item):
        return self._attributes[item]

@patch("main.storage.Client")
@patch("main.VertexAIEmbeddings")
@patch("main.PGVector")
@patch("main.PyPDFLoader")
def test_ingest_pdf_success(mock_loader, mock_pgvector, mock_embeddings, mock_storage):
    # Setup Mocks
    mock_bucket = MagicMock()
    mock_blob = MagicMock()
    mock_storage.return_value.bucket.return_value = mock_bucket
    mock_bucket.blob.return_value = mock_blob
    
    # Mock Async Methods
    mock_pgvector.return_value.add_documents = AsyncMock()
    
    # Mock PDF Load
    mock_doc = MagicMock(page_content="Test Content")
    mock_doc.metadata = {}
    mock_loader.return_value.load.return_value = [mock_doc]
    
    # Event Data
    data = {"bucket": "test-bucket", "name": "test-doc.pdf"}
    event = MockCloudEvent(data)
    
    # Run Function
    with patch("main.DB_PASSWORD", "test_pass"), \
         patch("main.DB_USER", "test_user"), \
         patch("main.DB_HOST", "localhost"), \
         patch("main.DB_NAME", "test_db"), \
         patch("main.PROJECT_ID", "test_project"):
        main.ingest_pdf(event)
    
    # Verify Download
    mock_blob.download_to_filename.assert_called()
    
    # Verify Loader called with temp path
    mock_loader.assert_called()
    
    # Verify Vector Store Add
    mock_pgvector.return_value.add_documents.assert_called()

@patch("main.storage.Client")
def test_ingest_pdf_skip_non_pdf(mock_storage):
    # Event Data
    data = {"bucket": "test-bucket", "name": "image.png"}
    event = MockCloudEvent(data)
    
    # Run Function
    main.ingest_pdf(event)
    
    # Verify NO Download
    mock_storage.return_value.bucket.assert_not_called()
