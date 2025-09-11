"""
Tests for pure Python S7 client implementation.
"""

import pytest
from unittest.mock import Mock, patch

from snap7.native_client import Client
from snap7.native.errors import S7ConnectionError
from snap7.type import Area


class TestNativeClient:
    """Test the pure Python S7 client."""
    
    def test_client_initialization(self):
        """Test client can be initialized."""
        client = Client()
        assert client is not None
        assert not client.get_connected()
    
    def test_context_manager(self):
        """Test client can be used as context manager."""
        with Client() as client:
            assert client is not None
    
    def test_connect_success(self):
        """Test successful connection."""
        # Setup mock
        client = Client()
        client._client = Mock()
        client._client.connect.return_value = client._client
        client._client.get_connected.return_value = True
        
        result = client.connect("192.168.1.10", 0, 1)
        
        assert result is client  # Should return self for chaining
        client._client.connect.assert_called_once_with("192.168.1.10", 0, 1, 102)
    
    def test_connect_invalid_parameters(self):
        """Test connection with invalid parameters."""
        client = Client()
        
        with pytest.raises(S7ConnectionError):
            client.connect("", 0, 1)  # Empty host
    
    def test_db_operations_not_connected(self):
        """Test DB operations fail when not connected."""
        client = Client()
        
        with pytest.raises(S7ConnectionError):
            client.db_read(1, 0, 10)
            
        with pytest.raises(S7ConnectionError):
            client.db_write(1, 0, bytearray(b'\x00\x01\x02'))
    
    def test_db_read_success(self):
        """Test successful DB read operation."""
        # Setup mock
        client = Client()
        client._client = Mock()
        client._client.db_read.return_value = bytearray(b'\x01\x02\x03\x04')
        
        data = client.db_read(1, 0, 4)
        
        assert isinstance(data, bytearray)
        assert len(data) == 4
        assert data == bytearray(b'\x01\x02\x03\x04')
    
    def test_db_write_success(self):
        """Test successful DB write operation."""
        # Setup mock
        client = Client()
        client._client = Mock()
        client._client.db_write.return_value = None
        
        test_data = bytearray(b'\x01\x02\x03\x04')
        
        # Should not raise exception
        client.db_write(1, 0, test_data)
        
        # Verify the underlying client was called correctly
        client._client.db_write.assert_called_once_with(1, 0, test_data)
    
    def test_area_operations(self):
        """Test area read/write operations."""
        # Setup mock
        client = Client()
        client._client = Mock()
        client._client.read_area.return_value = bytearray(b'\x00\x01')
        client._client.write_area.return_value = None
        
        # Test area read
        data = client.read_area(Area.MK, 0, 10, 2)
        assert len(data) == 2
        
        # Test area write
        test_data = bytearray(b'\x01\x02')
        client.write_area(Area.MK, 0, 10, test_data)
        
        # Verify calls
        client._client.read_area.assert_called_once_with(Area.MK, 0, 10, 2)
        client._client.write_area.assert_called_once_with(Area.MK, 0, 10, test_data)
    
    def test_convenience_methods(self):
        """Test convenience methods for different memory areas."""
        client = Client()
        
        # These should map to read_area calls
        with patch.object(client, 'read_area') as mock_read:
            client.eb_read(10, 4)
            mock_read.assert_called_with(Area.PE, 0, 10, 4)
            
            client.mb_read(20, 2)
            mock_read.assert_called_with(Area.MK, 0, 20, 2)
    
    def test_multi_var_operations(self):
        """Test multi-variable read/write operations."""
        # Setup mock
        client = Client()
        client._client = Mock()
        client._client.read_multi_vars.return_value = [bytearray(b'\x01'), bytearray(b'\x02')]
        client._client.write_multi_vars.return_value = None
        
        # Test multi read
        items = [
            {'area': Area.DB, 'db_number': 1, 'start': 0, 'size': 1},
            {'area': Area.MK, 'db_number': 0, 'start': 10, 'size': 1}
        ]
        results = client.read_multi_vars(items)
        assert len(results) == 2
        
        # Test multi write
        write_items = [
            {'area': Area.DB, 'db_number': 1, 'start': 0, 'data': bytearray(b'\x01')},
        ]
        client.write_multi_vars(write_items)
        
        # Verify calls
        client._client.read_multi_vars.assert_called_once_with(items)
        client._client.write_multi_vars.assert_called_once_with(write_items)
    
    def test_unimplemented_methods(self):
        """Test that unimplemented methods raise NotImplementedError."""
        client = Client()
        
        with pytest.raises(NotImplementedError):
            client.get_block_info(None, 1)
            
        with pytest.raises(NotImplementedError):
            client.upload(1)
            
        with pytest.raises(NotImplementedError):
            client.download(bytearray(), 1)
            
        with pytest.raises(NotImplementedError):
            client.db_get(1)
            
        with pytest.raises(NotImplementedError):
            client.set_session_password("test")
            
        with pytest.raises(NotImplementedError):
            client.clear_session_password()
            
        with pytest.raises(NotImplementedError):
            client.get_plc_datetime()
            
        with pytest.raises(NotImplementedError):
            client.set_plc_datetime(None)
            
        with pytest.raises(NotImplementedError):
            client.set_plc_system_datetime()
    
    def test_disconnect(self):
        """Test disconnect operation."""
        client = Client()
        client._client = Mock()
        client._client.disconnect.return_value = None
        
        client.disconnect()
        
        client._client.disconnect.assert_called_once()
    
    def test_create_and_destroy(self):
        """Test create and destroy methods for compatibility."""
        client = Client()
        
        # create() should be a no-op
        client.create()
        
        # destroy() should call disconnect
        with patch.object(client, 'disconnect') as mock_disconnect:
            client.destroy()
            mock_disconnect.assert_called_once()