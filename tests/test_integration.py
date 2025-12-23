"""
Tests for pure Python client integration.
"""

import pytest
import snap7
from snap7.client import Client as CtypesClient
from snap7.native.client import Client as PureClient


class TestIntegration:
    """Test the integration of pure Python client into the main library."""
    
    def test_get_client_default(self):
        """Test getting default ctypes client."""
        client = snap7.get_client()
        assert isinstance(client, CtypesClient)
        assert not isinstance(client, PureClient)
    
    def test_get_client_pure_python(self):
        """Test getting pure Python client."""
        client = snap7.get_client(pure_python=True)
        assert isinstance(client, PureClient)
        assert not isinstance(client, CtypesClient)
    
    def test_pure_client_direct_import(self):
        """Test direct import of pure Python client."""
        assert hasattr(snap7, 'PureClient')
        client = snap7.PureClient()
        assert isinstance(client, PureClient)
    
    def test_api_compatibility(self):
        """Test that both clients have compatible APIs."""
        ctypes_client = snap7.get_client(pure_python=False)
        pure_client = snap7.get_client(pure_python=True)
        
        # Both should have the same basic methods
        common_methods = [
            'connect', 'disconnect', 'get_connected',
            'db_read', 'db_write', 'read_area', 'write_area',
            'ab_read', 'ab_write', 'eb_read', 'eb_write',
            'mb_read', 'mb_write', 'tm_read', 'tm_write',
            'ct_read', 'ct_write', 'read_multi_vars', 'write_multi_vars'
        ]
        
        for method in common_methods:
            assert hasattr(ctypes_client, method), f"CtypesClient missing {method}"
            assert hasattr(pure_client, method), f"PureClient missing {method}"
            assert callable(getattr(ctypes_client, method)), f"CtypesClient.{method} not callable"
            assert callable(getattr(pure_client, method)), f"PureClient.{method} not callable"
    
    def test_context_manager_compatibility(self):
        """Test both clients work as context managers."""
        # Ctypes client
        with snap7.get_client(pure_python=False) as client:
            assert isinstance(client, CtypesClient)
        
        # Pure Python client
        with snap7.get_client(pure_python=True) as client:
            assert isinstance(client, PureClient)
    
    def test_imports_and_exports(self):
        """Test that all expected symbols are exported."""
        # Standard exports should be available
        assert hasattr(snap7, 'Client')
        assert hasattr(snap7, 'Area')
        assert hasattr(snap7, 'Block')
        assert hasattr(snap7, 'WordLen')
        assert hasattr(snap7, 'get_client')
        
        # Pure Python client should be available
        assert hasattr(snap7, 'PureClient')
        
        # Check __all__ includes new symbols
        assert 'get_client' in snap7.__all__
        assert 'PureClient' in snap7.__all__
    
    def test_method_signatures_match(self):
        """Test that key method signatures match between implementations."""
        ctypes_client = snap7.get_client(pure_python=False)
        pure_client = snap7.get_client(pure_python=True)
        
        # Test connect method signatures
        import inspect
        
        ctypes_connect = inspect.signature(ctypes_client.connect)
        pure_connect = inspect.signature(pure_client.connect)
        
        # Both should accept similar parameters
        # (exact signature match not required due to different implementations)
        assert 'address' in ctypes_connect.parameters or len(ctypes_connect.parameters) >= 3
        assert 'address' in pure_connect.parameters or len(pure_connect.parameters) >= 3
    
    def test_error_handling_compatibility(self):
        """Test that both clients handle errors in compatible ways."""
        ctypes_client = snap7.get_client(pure_python=False)
        pure_client = snap7.get_client(pure_python=True)
        
        # Both should raise exceptions for invalid operations when not connected
        with pytest.raises(Exception):  # Could be different exception types
            ctypes_client.db_read(1, 0, 4)
            
        with pytest.raises(Exception):  # Could be different exception types  
            pure_client.db_read(1, 0, 4)