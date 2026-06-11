import pytest
from unittest.mock import MagicMock
from chains.rag_chain import format_docs

def test_format_docs_multiple_documents():
    docs = [
        MagicMock(page_content="Content 1"),
        MagicMock(page_content="Content 2"),
    ]
    result = format_docs(docs)
    assert result == "Content 1\n\nContent 2"

def test_format_docs_single_document():
    docs = [MagicMock(page_content="Only content")]
    result = format_docs(docs)
    assert result == "Only content"

def test_format_docs_empty_list():
    result = format_docs([])
    assert result == ""
