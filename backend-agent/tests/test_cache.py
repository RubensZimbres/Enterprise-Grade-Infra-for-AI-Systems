import pytest
from unittest.mock import MagicMock, patch
import sys
import importlib.util

# Setup mocks for dependencies BEFORE importing the real module
mock_genai = MagicMock()
mock_genai_types = MagicMock()
# This ensures that 'from google.genai.types import CreateCachedContentConfig' works
mock_genai.types = mock_genai_types

# Patch sys.modules to include the mocks
with patch.dict(sys.modules, {
    "google.genai": mock_genai,
    "google.genai.types": mock_genai_types,
    "config": MagicMock()
}):
    # Load the real module
    spec = importlib.util.spec_from_file_location("cache_manager_real", "cache_manager.py")
    cache_manager_real = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(cache_manager_real)

def test_cache_manager_creation():
    # Test the class initialization
    # We need to patch the client on the loaded module's namespace or the mock we injected
    with patch("google.genai.Client") as MockClient:
        # Reset the mock because the module import already triggered one call (the singleton)
        cache_manager_real.genai.Client.reset_mock()
        
        # Access the CacheManager class from the loaded module
        CacheManager = cache_manager_real.CacheManager
        
        # We need to ensure the Client call inside __init__ uses our mock
        # cache_manager_real.genai.Client is the one being called.
        
        cm = CacheManager()
        assert cm.ttl == "3600s"
        # Verify Client was called
        cache_manager_real.genai.Client.assert_called_once()

def test_get_or_create_cache_success():
    CacheManager = cache_manager_real.CacheManager
    
    # We can configure the mock client directly since we have a reference to the module's imports
    mock_client_cls = cache_manager_real.genai.Client
    mock_client_instance = mock_client_cls.return_value
    
    mock_cache_obj = MagicMock()
    mock_cache_obj.name = "projects/123/caches/abc"
    mock_cache_obj.expire_time = "tomorrow"
    mock_client_instance.caches.create.return_value = mock_cache_obj
    
    cm = CacheManager()
    result = cm.get_or_create_cache()
    
    assert result == "projects/123/caches/abc"
    assert cm.cache_name == "projects/123/caches/abc"
    mock_client_instance.caches.create.assert_called_once()

def test_get_or_create_cache_failure():
    CacheManager = cache_manager_real.CacheManager
    
    mock_client_cls = cache_manager_real.genai.Client
    mock_client_instance = mock_client_cls.return_value
    mock_client_instance.caches.create.side_effect = Exception("API Error")
    
    cm = CacheManager()
    result = cm.get_or_create_cache()
    
    assert result is None
