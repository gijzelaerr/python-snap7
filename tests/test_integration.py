"""
Tests for Python S7 client integration.
"""

import pytest
import snap7
from snap7.client import Client


class TestIntegration:
    """Test the integration of the S7 client into the main library."""

    def test_client_creation(self):
        """Test creating a client."""
        client = snap7.Client()
        assert isinstance(client, Client)

    def test_direct_import(self):
        """Test direct import of Client."""
        assert hasattr(snap7, "Client")
        client = snap7.Client()
        assert isinstance(client, Client)

    def test_client_api(self):
        """Test that client has expected API methods."""
        client = snap7.Client()

        # Should have the basic methods
        common_methods = [
            "connect",
            "disconnect",
            "get_connected",
            "db_read",
            "db_write",
            "read_area",
            "write_area",
            "ab_read",
            "ab_write",
            "eb_read",
            "eb_write",
            "mb_read",
            "mb_write",
            "tm_read",
            "tm_write",
            "ct_read",
            "ct_write",
            "read_multi_vars",
            "write_multi_vars",
        ]

        for method in common_methods:
            assert hasattr(client, method), f"Client missing {method}"
            assert callable(getattr(client, method)), f"Client.{method} not callable"

    def test_context_manager(self):
        """Test client works as a context manager."""
        with snap7.Client() as client:
            assert isinstance(client, Client)

    def test_imports_and_exports(self):
        """Test that all expected symbols are exported."""
        # Standard exports should be available
        assert hasattr(snap7, "Client")
        assert hasattr(snap7, "Server")
        assert hasattr(snap7, "Partner")
        assert hasattr(snap7, "Logo")
        assert hasattr(snap7, "Area")
        assert hasattr(snap7, "Block")
        assert hasattr(snap7, "WordLen")

        # Check __all__ includes expected symbols
        assert "Client" in snap7.__all__
        assert "Server" in snap7.__all__
        assert "Partner" in snap7.__all__
        assert "Area" in snap7.__all__

    def test_method_signature(self):
        """Test that key method signatures are correct."""
        client = snap7.Client()

        import inspect

        connect_sig = inspect.signature(client.connect)

        # Should accept address, rack, slot, tcp_port
        assert "address" in connect_sig.parameters or len(connect_sig.parameters) >= 3

    def test_error_handling(self):
        """Test that client handles errors properly."""
        client = snap7.Client()

        # Should raise exception for operation when not connected
        with pytest.raises(Exception):
            client.db_read(1, 0, 4)
