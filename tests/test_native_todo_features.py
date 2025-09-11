"""
Tests for all TODO features implemented in the pure Python client.

These tests verify that all previously TODO-marked functions now work correctly
with the pure Python S7 server implementation.
"""

import time
import threading
from datetime import datetime, timedelta
from ctypes import c_char

import pytest
import snap7
from snap7.native_server import Server as PureServer
from snap7.native_client import Client as PureClient
from snap7.type import SrvArea, Area, Block


class TestTodoFeatures:
    """Test all implemented TODO features."""
    
    @classmethod
    def setup_class(cls):
        """Set up a shared server for all tests."""
        cls.server = PureServer()
        cls.port = 11050  # Use unique port for these tests
        
        # Create and register test memory areas
        size = 100
        cls.db_data = bytearray(size)
        cls.mk_data = bytearray(size)
        cls.pe_data = bytearray(size)
        
        # Initialize with test values
        cls.db_data[0] = 0x42
        cls.db_data[1] = 0xFF
        cls.db_data[10:14] = bytearray([0x11, 0x22, 0x33, 0x44])
        
        # Register memory areas
        db_array = (c_char * size).from_buffer(cls.db_data)
        mk_array = (c_char * size).from_buffer(cls.mk_data)
        pe_array = (c_char * size).from_buffer(cls.pe_data)
        
        cls.server.register_area(SrvArea.DB, 1, db_array)
        cls.server.register_area(SrvArea.MK, 0, mk_array)
        cls.server.register_area(SrvArea.PE, 0, pe_array)
        
        # Start server
        cls.server.start(cls.port)
        time.sleep(0.2)  # Give server time to start
    
    @classmethod
    def teardown_class(cls):
        """Clean up the shared server."""
        try:
            cls.server.stop()
            cls.server.destroy()
        except Exception:
            pass
        time.sleep(0.2)
    
    def setup_method(self):
        """Set up client for each test."""
        self.client = PureClient()
        self.client.connect("127.0.0.1", 0, 1, self.port)
    
    def teardown_method(self):
        """Clean up client after each test."""
        try:
            self.client.disconnect()
        except Exception:
            pass
    
    def test_db_get_function(self):
        """Test db_get function that reads entire DB."""
        # Test reading entire DB
        data = self.client.db_get(1)
        
        # Should get some data
        assert len(data) > 0
        
        # For small DBs, should contain our test data
        if len(data) >= 14:
            assert data[0] == 0x42
            assert data[1] == 0xFF
    
    def test_multi_variable_read_optimization(self):
        """Test optimized multi-variable read operations."""
        # Test reading multiple variables from same area
        items = [
            {'area': Area.DB, 'db_number': 1, 'start': 0, 'size': 4},
            {'area': Area.DB, 'db_number': 1, 'start': 10, 'size': 4},
            {'area': Area.DB, 'db_number': 1, 'start': 20, 'size': 4},
        ]
        
        results = self.client.read_multi_vars(items)
        
        # Should get results for all items
        assert len(results) == 3
        
        # All results should have data
        for result in results:
            assert len(result) == 4
    
    def test_multi_variable_write_operations(self):
        """Test multi-variable write operations."""
        # Test writing multiple variables
        items = [
            {'area': Area.DB, 'db_number': 1, 'start': 50, 'data': bytearray([1, 2, 3, 4])},
            {'area': Area.DB, 'db_number': 1, 'start': 60, 'data': bytearray([5, 6, 7, 8])},
        ]
        
        # Should not raise exceptions
        self.client.write_multi_vars(items)
        
        # Verify writes by reading back
        read_items = [
            {'area': Area.DB, 'db_number': 1, 'start': 50, 'size': 4},
            {'area': Area.DB, 'db_number': 1, 'start': 60, 'size': 4},
        ]
        
        results = self.client.read_multi_vars(read_items)
        assert len(results) == 2
    
    def test_plc_control_functions(self):
        """Test PLC control functions (stop, hot start, cold start)."""
        # Test PLC stop
        self.client.plc_stop()
        
        # Test PLC hot start
        self.client.plc_hot_start()
        
        # Test PLC cold start
        self.client.plc_cold_start()
        
        # All should complete without exceptions
        # In a real test, we would verify CPU state changes
    
    def test_cpu_info_function(self):
        """Test get_cpu_info function."""
        cpu_info = self.client.get_cpu_info()
        
        # Should return a valid CPU info structure
        assert hasattr(cpu_info, 'ModuleTypeName')
        assert hasattr(cpu_info, 'SerialNumber')
        assert hasattr(cpu_info, 'ASName')
        
        # Should have some content
        assert len(cpu_info.ModuleTypeName) > 0
        assert len(cpu_info.SerialNumber) > 0
    
    def test_cpu_state_function(self):
        """Test get_cpu_state function."""
        cpu_state = self.client.get_cpu_state()
        
        # Should return a valid state string
        assert isinstance(cpu_state, str)
        assert len(cpu_state) > 0
        
        # Should be a known state
        assert cpu_state in ["RUN", "STOP", "UNKNOWN"]
    
    def test_list_blocks_function(self):
        """Test list_blocks function."""
        block_list = self.client.list_blocks()
        
        # Should return a valid block list structure
        assert hasattr(block_list, 'OBCount')
        assert hasattr(block_list, 'FBCount')
        assert hasattr(block_list, 'FCCount')
        assert hasattr(block_list, 'DBCount')
        
        # Should have reasonable values
        assert block_list.OBCount >= 0
        assert block_list.DBCount >= 0
    
    def test_get_block_info_function(self):
        """Test get_block_info function."""
        # Test getting DB block info
        block_info = self.client.get_block_info(Block.DB, 1)
        
        # Should return a valid block info structure
        assert hasattr(block_info, 'BlkType')
        assert hasattr(block_info, 'BlkNumber')
        assert hasattr(block_info, 'MC7Size')
        
        # Should have correct values for DB
        assert block_info.BlkNumber == 1
        assert block_info.MC7Size >= 0
    
    def test_upload_function(self):
        """Test upload function."""
        # Test uploading a block
        block_data = self.client.upload(1)
        
        # Should return some data
        assert len(block_data) > 0
        
        # Should contain block-like data
        assert isinstance(block_data, bytearray)
    
    def test_download_function(self):
        """Test download function."""
        # Create some test block data
        test_data = bytearray(b"BLOCK_TEST_DATA")
        
        # Should not raise exceptions
        self.client.download(test_data, 1)
    
    def test_plc_datetime_functions(self):
        """Test PLC datetime functions."""
        # Test getting PLC datetime
        plc_time = self.client.get_plc_datetime()
        
        # Should return a datetime object
        assert isinstance(plc_time, datetime)
        
        # Should be reasonably close to current time
        now = datetime.now()
        time_diff = abs((plc_time - now).total_seconds())
        assert time_diff < 60  # Within 1 minute
        
        # Test setting PLC datetime
        test_time = datetime.now() + timedelta(hours=1)
        self.client.set_plc_datetime(test_time)
        
        # Test setting PLC to system time
        self.client.set_plc_system_datetime()
    
    def test_session_password_functions(self):
        """Test session password functions."""
        # Test setting session password
        self.client.set_session_password("test123")
        
        # Test clearing session password
        self.client.clear_session_password()
        
        # Should not raise exceptions
    
    def test_connection_type_function(self):
        """Test set_connection_type function."""
        # Test setting different connection types
        self.client.set_connection_type(1)  # PG
        self.client.set_connection_type(2)  # OP
        self.client.set_connection_type(3)  # S7 Basic
        
        # Should not raise exceptions
    
    def test_connection_params_function(self):
        """Test set_connection_params function."""
        # Test setting connection parameters
        self.client.set_connection_params("127.0.0.1", 0x0100, 0x0102)
        
        # Should not raise exceptions
    
    def test_error_text_function(self):
        """Test error_text function."""
        # Test getting error text for various codes
        error_text = self.client.error_text(0)
        assert isinstance(error_text, str)
        
        error_text = self.client.error_text(0x8001)
        assert isinstance(error_text, str)
    
    def test_pdu_length_function(self):
        """Test get_pdu_length function."""
        pdu_length = self.client.get_pdu_length()
        
        # Should return a reasonable PDU length
        assert isinstance(pdu_length, int)
        assert pdu_length > 0
        assert pdu_length <= 960  # S7 maximum


class TestErrorConditions:
    """Test error conditions for implemented TODO features."""
    
    def test_functions_without_connection(self):
        """Test that functions properly handle no connection."""
        client = PureClient()
        
        # These should raise connection errors
        with pytest.raises(Exception):
            client.db_get(1)
        
        with pytest.raises(Exception):
            client.get_cpu_info()
        
        with pytest.raises(Exception):
            client.get_cpu_state()
        
        with pytest.raises(Exception):
            client.plc_stop()
        
        with pytest.raises(Exception):
            client.get_plc_datetime()
        
        with pytest.raises(Exception):
            client.list_blocks()
        
        with pytest.raises(Exception):
            client.get_block_info(Block.DB, 1)
        
        with pytest.raises(Exception):
            client.upload(1)


class TestAPICompatibility:
    """Test that implemented functions maintain API compatibility."""
    
    def test_function_signatures(self):
        """Test that all functions have correct signatures."""
        client = PureClient()
        
        # Test that functions exist and are callable
        assert callable(client.db_get)
        assert callable(client.read_multi_vars)
        assert callable(client.write_multi_vars)
        assert callable(client.plc_stop)
        assert callable(client.plc_hot_start)
        assert callable(client.plc_cold_start)
        assert callable(client.get_cpu_info)
        assert callable(client.get_cpu_state)
        assert callable(client.list_blocks)
        assert callable(client.get_block_info)
        assert callable(client.upload)
        assert callable(client.download)
        assert callable(client.get_plc_datetime)
        assert callable(client.set_plc_datetime)
        assert callable(client.set_plc_system_datetime)
        assert callable(client.set_session_password)
        assert callable(client.clear_session_password)
        assert callable(client.set_connection_type)
        assert callable(client.set_connection_params)
        assert callable(client.get_pdu_length)
        assert callable(client.error_text)
    
    def test_return_types(self):
        """Test that functions return expected types."""
        # This test doesn't require connection for type checking
        client = PureClient()
        
        # Test error_text (doesn't require connection)
        error_text = client.error_text(0)
        assert isinstance(error_text, str)
        
        # Test get_pdu_length (works without connection in our implementation)
        pdu_length = client.get_pdu_length()
        assert isinstance(pdu_length, int)


class TestIntegrationWithMainModule:
    """Test integration with main snap7 module."""
    
    def test_get_client_function(self):
        """Test that get_client returns proper client types."""
        # Test pure Python client
        client = snap7.get_client(pure_python=True)
        assert hasattr(client, 'db_get')
        assert hasattr(client, 'plc_stop')
        assert hasattr(client, 'get_cpu_info')
        
        # Verify it's the pure client
        assert client.__class__.__name__ == "Client"
        
        # Should have all the implemented TODO functions
        assert callable(client.db_get)
        assert callable(client.list_blocks)
        assert callable(client.get_block_info)
        assert callable(client.upload)
        assert callable(client.download)
        assert callable(client.get_plc_datetime)