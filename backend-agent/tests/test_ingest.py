import pytest
from unittest.mock import MagicMock, patch
import sys

# Because conftest.py mocks modules globally, we can use those mocks or patch them further.
# However, ingest.py imports classes directly.
# We need to test the logic inside ingest_data.

from ingest import ingest_data

@pytest.mark.asyncio
async def test_ingest_data_success():
    # We need to patch the classes used in ingest.py
    # Since they are imported as: from langchain_community.document_loaders import DirectoryLoader
    # We patch 'ingest.DirectoryLoader', 'ingest.PyPDFLoader', etc.
    
    with patch("ingest.os.path.exists", return_value=True), \
         patch("ingest.DirectoryLoader") as MockLoader, \
         patch("ingest.RecursiveCharacterTextSplitter") as MockSplitter, \
         patch("ingest.VertexAIEmbeddings") as MockEmbeddings, \
         patch("ingest.PGVector") as MockPGVector:
        
        # Setup mocks
        mock_loader_instance = MockLoader.return_value
        mock_loader_instance.load.return_value = [MagicMock(page_content="doc1"), MagicMock(page_content="doc2")]
        
        mock_splitter_instance = MockSplitter.return_value
        mock_splitter_instance.split_documents.return_value = ["chunk1", "chunk2", "chunk3"]
        
        mock_vector_store = MockPGVector.return_value
        # add_documents is async
        mock_vector_store.add_documents = MagicMock()
        async def async_add_docs(docs):
             return
        mock_vector_store.add_documents.side_effect = async_add_docs

        # Run the function
        await ingest_data()
        
        # Verify
        MockLoader.assert_called_once()
        mock_loader_instance.load.assert_called_once()
        
        MockSplitter.assert_called_once()
        mock_splitter_instance.split_documents.assert_called_once()
        
        MockEmbeddings.assert_called_once()
        MockPGVector.assert_called_once()
        mock_vector_store.add_documents.assert_called_once()

@pytest.mark.asyncio
async def test_ingest_data_no_docs():
    with patch("ingest.os.path.exists", return_value=True), \
         patch("ingest.DirectoryLoader") as MockLoader:
        
        mock_loader_instance = MockLoader.return_value
        mock_loader_instance.load.return_value = [] # Empty list
        
        await ingest_data()
        
        MockLoader.assert_called_once()
        # Should exit early
        with patch("ingest.RecursiveCharacterTextSplitter") as MockSplitter:
            MockSplitter.assert_not_called()
