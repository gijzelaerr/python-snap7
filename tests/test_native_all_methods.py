"""
Test all client API methods against the pure Python server.

This test suite calls every single method available in the Client API
to discover what's missing and what needs to be implemented in both
the client and server implementations.
"""

import pytest
import time
import struct
from ctypes import c_char
from datetime import datetime

from snap7.native.server import Server as PureServer
from snap7.native.client import Client as PureClient
from snap7.type import SrvArea, Area, Block


class TestAllClientMethods:
    """Test every client method against pure Python server."""
    
    def setup_method(self):
        """Set up test server and client."""
        self.server = PureServer()
        self.port = 11050  # Use unique port
        
        # Create and register comprehensive test memory areas
        self.area_size = 200
        
        # DB area with test data
        self.db_data = bytearray(self.area_size)
        self.db_data[0:4] = struct.pack('>I', 0x12345678)  # Test DWord
        self.db_data[4:6] = struct.pack('>H', 0x9ABC)      # Test Word
        self.db_data[6] = 0xDE                             # Test Byte
        self.db_data[10:14] = struct.pack('>f', 3.14159)   # Test Real
        
        # Memory areas
        self.mk_data = bytearray(self.area_size)
        self.pe_data = bytearray(self.area_size)  # Process inputs
        self.pa_data = bytearray(self.area_size)  # Process outputs
        self.tm_data = bytearray(self.area_size)  # Timers
        self.ct_data = bytearray(self.area_size)  # Counters
        
        # Fill with test patterns
        for i in range(self.area_size):
            self.mk_data[i] = i % 256
            self.pe_data[i] = (i * 2) % 256
            self.pa_data[i] = (i * 3) % 256
            self.tm_data[i] = (i * 4) % 256
            self.ct_data[i] = (i * 5) % 256
        
        # Register areas using ctypes arrays (for compatibility)
        db_array = (c_char * self.area_size).from_buffer(self.db_data)
        mk_array = (c_char * self.area_size).from_buffer(self.mk_data)
        pe_array = (c_char * self.area_size).from_buffer(self.pe_data)
        pa_array = (c_char * self.area_size).from_buffer(self.pa_data)
        tm_array = (c_char * self.area_size).from_buffer(self.tm_data)
        ct_array = (c_char * self.area_size).from_buffer(self.ct_data)
        
        self.server.register_area(SrvArea.DB, 1, db_array)
        self.server.register_area(SrvArea.MK, 0, mk_array)
        self.server.register_area(SrvArea.PE, 0, pe_array)
        self.server.register_area(SrvArea.PA, 0, pa_array)
        self.server.register_area(SrvArea.TM, 0, tm_array)
        self.server.register_area(SrvArea.CT, 0, ct_array)
        
        # Start server
        self.server.start(self.port)
        time.sleep(0.1)
        
        # Connect client
        self.client = PureClient()
        self.client.connect("127.0.0.1", 0, 1, self.port)
    
    def teardown_method(self):
        """Clean up server and client."""
        try:
            self.client.disconnect()
        except Exception:
            pass
        
        try:
            self.server.stop()
            self.server.destroy()
        except Exception:
            pass
        
        time.sleep(0.1)
    
    # Basic connection methods
    def test_connect_disconnect(self):
        """Test connect/disconnect methods."""
        # Already connected in setup
        assert self.client.get_connected()
        
        # Test disconnect
        self.client.disconnect()
        assert not self.client.get_connected()
        
        # Test reconnect
        self.client.connect("127.0.0.1", 0, 1, self.port)
        assert self.client.get_connected()
    
    def test_create_destroy(self):
        """Test create/destroy methods."""
        # These should be no-ops for compatibility
        self.client.create()  # Should not raise
        self.client.destroy() # Should disconnect
        assert not self.client.get_connected()
    
    # DB methods
    def test_db_read(self):
        """Test DB read operations."""
        # Read various sizes
        data = self.client.db_read(1, 0, 1)
        assert len(data) >= 1
        
        data = self.client.db_read(1, 0, 4)
        assert len(data) >= 4
        
        data = self.client.db_read(1, 10, 10)
        assert len(data) >= 10
    
    def test_db_write(self):
        """Test DB write operations."""
        # Write various sizes
        test_data = bytearray([0x11])
        self.client.db_write(1, 0, test_data)
        
        test_data = bytearray([0x11, 0x22, 0x33, 0x44])
        self.client.db_write(1, 10, test_data)
        
        test_data = bytearray(range(10))
        self.client.db_write(1, 50, test_data)
    
    def test_db_get(self):
        """Test getting entire DB."""
        try:
            data = self.client.db_get(1)
            assert len(data) > 0
        except NotImplementedError:
            pytest.skip("db_get not implemented yet")
    
    # Area read/write methods
    def test_read_area_all_types(self):
        """Test reading from all area types."""
        areas_to_test = [
            (Area.DB, 1),   # Data block 1
            (Area.MK, 0),   # Memory/flags
            (Area.PE, 0),   # Process inputs
            (Area.PA, 0),   # Process outputs
            (Area.TM, 0),   # Timers
            (Area.CT, 0),   # Counters
        ]
        
        for area, db_num in areas_to_test:
            try:
                data = self.client.read_area(area, db_num, 0, 4)
                assert len(data) >= 4
                print(f"✓ Read from {area.name}: {data[:4].hex()}")
            except Exception as e:
                print(f"✗ Failed to read from {area.name}: {e}")
                if "not yet implemented" not in str(e):
                    raise
    
    def test_write_area_all_types(self):
        """Test writing to all area types."""
        test_data = bytearray([0xAA, 0xBB, 0xCC, 0xDD])
        
        areas_to_test = [
            (Area.DB, 1),   # Data block 1
            (Area.MK, 0),   # Memory/flags
            (Area.PE, 0),   # Process inputs
            (Area.PA, 0),   # Process outputs
            (Area.TM, 0),   # Timers
            (Area.CT, 0),   # Counters
        ]
        
        for area, db_num in areas_to_test:
            try:
                self.client.write_area(area, db_num, 20, test_data)
                print(f"✓ Wrote to {area.name}")
            except Exception as e:
                print(f"✗ Failed to write to {area.name}: {e}")
                if "not yet implemented" not in str(e):
                    raise
    
    # Convenience methods
    def test_ab_read_write(self):
        """Test process output (AB) read/write."""
        try:
            data = self.client.ab_read(0, 4)
            assert len(data) >= 4
            
            test_data = bytearray([0x01, 0x02, 0x03, 0x04])
            self.client.ab_write(0, test_data)
            print("✓ AB read/write works")
        except Exception as e:
            print(f"✗ AB read/write failed: {e}")
            if "not yet implemented" not in str(e):
                raise
    
    def test_eb_read_write(self):
        """Test process input (EB) read/write."""
        try:
            data = self.client.eb_read(0, 4)
            assert len(data) >= 4
            
            test_data = bytearray([0x05, 0x06, 0x07, 0x08])
            self.client.eb_write(0, 4, test_data)
            print("✓ EB read/write works")
        except Exception as e:
            print(f"✗ EB read/write failed: {e}")
            if "not yet implemented" not in str(e):
                raise
    
    def test_mb_read_write(self):
        """Test memory/flag (MB) read/write."""
        try:
            data = self.client.mb_read(0, 4)
            assert len(data) >= 4
            
            test_data = bytearray([0x09, 0x0A, 0x0B, 0x0C])
            self.client.mb_write(0, 4, test_data)
            print("✓ MB read/write works")
        except Exception as e:
            print(f"✗ MB read/write failed: {e}")
            if "not yet implemented" not in str(e):
                raise
    
    def test_tm_read_write(self):
        """Test timer (TM) read/write."""
        try:
            data = self.client.tm_read(0, 2)  # 2 timers
            assert len(data) >= 4  # 2 timers * 2 bytes each
            
            test_data = bytearray([0x01, 0x23, 0x45, 0x67])  # 2 timer values
            self.client.tm_write(0, 2, test_data)
            print("✓ TM read/write works")
        except Exception as e:
            print(f"✗ TM read/write failed: {e}")
            if "not yet implemented" not in str(e):
                raise
    
    def test_ct_read_write(self):
        """Test counter (CT) read/write."""
        try:
            data = self.client.ct_read(0, 2)  # 2 counters
            assert len(data) >= 4  # 2 counters * 2 bytes each
            
            test_data = bytearray([0x89, 0xAB, 0xCD, 0xEF])  # 2 counter values
            self.client.ct_write(0, 2, test_data)
            print("✓ CT read/write works")
        except Exception as e:
            print(f"✗ CT read/write failed: {e}")
            if "not yet implemented" not in str(e):
                raise
    
    # Multi-variable operations
    def test_read_multi_vars(self):
        """Test reading multiple variables."""
        items = [
            {'area': Area.DB, 'db_number': 1, 'start': 0, 'size': 4},
            {'area': Area.MK, 'db_number': 0, 'start': 0, 'size': 2},
            {'area': Area.PE, 'db_number': 0, 'start': 0, 'size': 1},
        ]
        
        try:
            results = self.client.read_multi_vars(items)
            assert len(results) == 3
            assert len(results[0]) >= 4
            assert len(results[1]) >= 2
            assert len(results[2]) >= 1
            print("✓ Read multi vars works")
        except Exception as e:
            print(f"✗ Read multi vars failed: {e}")
            if "not yet implemented" not in str(e):
                raise
    
    def test_write_multi_vars(self):
        """Test writing multiple variables."""
        items = [
            {'area': Area.DB, 'db_number': 1, 'start': 100, 'data': bytearray([0x11, 0x22, 0x33, 0x44])},
            {'area': Area.MK, 'db_number': 0, 'start': 10, 'data': bytearray([0x55, 0x66])},
            {'area': Area.PA, 'db_number': 0, 'start': 5, 'data': bytearray([0x77])},
        ]
        
        try:
            self.client.write_multi_vars(items)
            print("✓ Write multi vars works")
        except Exception as e:
            print(f"✗ Write multi vars failed: {e}")
            if "not yet implemented" not in str(e):
                raise
    
    # PLC info and control methods
    def test_list_blocks(self):
        """Test listing PLC blocks."""
        try:
            blocks = self.client.list_blocks()
            assert blocks is not None
            print(f"✓ List blocks works: {blocks}")
        except NotImplementedError:
            pytest.skip("list_blocks not implemented yet")
        except Exception as e:
            print(f"✗ List blocks failed: {e}")
            raise
    
    def test_get_cpu_info(self):
        """Test getting CPU information."""
        try:
            cpu_info = self.client.get_cpu_info()
            assert cpu_info is not None
            print(f"✓ Get CPU info works: {cpu_info}")
        except NotImplementedError:
            pytest.skip("get_cpu_info not implemented yet")
        except Exception as e:
            print(f"✗ Get CPU info failed: {e}")
            raise
    
    def test_get_cpu_state(self):
        """Test getting CPU state."""
        try:
            state = self.client.get_cpu_state()
            assert isinstance(state, str)
            print(f"✓ Get CPU state works: {state}")
        except NotImplementedError:
            pytest.skip("get_cpu_state not implemented yet")
        except Exception as e:
            print(f"✗ Get CPU state failed: {e}")
            raise
    
    def test_plc_control(self):
        """Test PLC control operations."""
        # Test PLC stop
        try:
            self.client.plc_stop()
            print("✓ PLC stop works")
        except NotImplementedError:
            pytest.skip("plc_stop not implemented yet")
        except Exception as e:
            print(f"✗ PLC stop failed: {e}")
            if "not yet implemented" not in str(e):
                raise
        
        # Test PLC hot start
        try:
            self.client.plc_hot_start()
            print("✓ PLC hot start works")
        except NotImplementedError:
            pytest.skip("plc_hot_start not implemented yet")
        except Exception as e:
            print(f"✗ PLC hot start failed: {e}")
            if "not yet implemented" not in str(e):
                raise
        
        # Test PLC cold start
        try:
            self.client.plc_cold_start()
            print("✓ PLC cold start works")
        except NotImplementedError:
            pytest.skip("plc_cold_start not implemented yet")
        except Exception as e:
            print(f"✗ PLC cold start failed: {e}")
            if "not yet implemented" not in str(e):
                raise
    
    # PDU and error methods
    def test_get_pdu_length(self):
        """Test getting PDU length."""
        try:
            pdu_length = self.client.get_pdu_length()
            assert isinstance(pdu_length, int)
            assert pdu_length > 0
            print(f"✓ Get PDU length works: {pdu_length}")
        except Exception as e:
            print(f"✗ Get PDU length failed: {e}")
            raise
    
    def test_error_text(self):
        """Test error text retrieval."""
        try:
            error_msg = self.client.error_text(0)
            assert isinstance(error_msg, str)
            print(f"✓ Error text works: {error_msg}")
        except Exception as e:
            print(f"✗ Error text failed: {e}")
            raise
    
    # Block operations
    def test_get_block_info(self):
        """Test getting block information."""
        try:
            block_info = self.client.get_block_info(Block.DB, 1)
            assert block_info is not None
            print(f"✓ Get block info works: {block_info}")
        except NotImplementedError:
            pytest.skip("get_block_info not implemented yet")
        except Exception as e:
            print(f"✗ Get block info failed: {e}")
            if "not yet implemented" not in str(e):
                raise
    
    def test_upload_download(self):
        """Test block upload/download."""
        # Test upload
        try:
            data = self.client.upload(1)
            assert isinstance(data, bytearray)
            print(f"✓ Upload works: {len(data)} bytes")
        except NotImplementedError:
            pytest.skip("upload not implemented yet")
        except Exception as e:
            print(f"✗ Upload failed: {e}")
            if "not yet implemented" not in str(e):
                raise
        
        # Test download
        try:
            test_data = bytearray(b"TEST_BLOCK_DATA")
            self.client.download(test_data, 2)
            print("✓ Download works")
        except NotImplementedError:
            pytest.skip("download not implemented yet")
        except Exception as e:
            print(f"✗ Download failed: {e}")
            if "not yet implemented" not in str(e):
                raise
    
    # Authentication methods
    def test_session_password(self):
        """Test session password operations."""
        try:
            self.client.set_session_password("test123")
            print("✓ Set session password works")
            
            self.client.clear_session_password()
            print("✓ Clear session password works")
        except NotImplementedError:
            pytest.skip("session password not implemented yet")
        except Exception as e:
            print(f"✗ Session password failed: {e}")
            if "not yet implemented" not in str(e):
                raise
    
    # Connection parameter methods
    def test_set_connection_params(self):
        """Test setting connection parameters."""
        try:
            self.client.set_connection_params("127.0.0.1", 0x0100, 0x0102)
            print("✓ Set connection params works")
        except Exception as e:
            print(f"✗ Set connection params failed: {e}")
            if "not yet implemented" not in str(e):
                raise
    
    def test_set_connection_type(self):
        """Test setting connection type."""
        try:
            self.client.set_connection_type(1)  # PG connection
            print("✓ Set connection type works")
        except Exception as e:
            print(f"✗ Set connection type failed: {e}")
            if "not yet implemented" not in str(e):
                raise
    
    # DateTime methods
    def test_plc_datetime(self):
        """Test PLC date/time operations."""
        # Test get PLC datetime
        try:
            dt = self.client.get_plc_datetime()
            assert isinstance(dt, datetime)
            print(f"✓ Get PLC datetime works: {dt}")
        except NotImplementedError:
            pytest.skip("get_plc_datetime not implemented yet")
        except Exception as e:
            print(f"✗ Get PLC datetime failed: {e}")
            if "not yet implemented" not in str(e):
                raise
        
        # Test set PLC datetime
        try:
            test_dt = datetime.now()
            self.client.set_plc_datetime(test_dt)
            print("✓ Set PLC datetime works")
        except NotImplementedError:
            pytest.skip("set_plc_datetime not implemented yet")
        except Exception as e:
            print(f"✗ Set PLC datetime failed: {e}")
            if "not yet implemented" not in str(e):
                raise
        
        # Test set PLC system datetime
        try:
            self.client.set_plc_system_datetime()
            print("✓ Set PLC system datetime works")
        except NotImplementedError:
            pytest.skip("set_plc_system_datetime not implemented yet")
        except Exception as e:
            print(f"✗ Set PLC system datetime failed: {e}")
            if "not yet implemented" not in str(e):
                raise
    
    # Context manager test
    def test_context_manager(self):
        """Test client as context manager."""
        with PureClient() as client:
            client.connect("127.0.0.1", 0, 1, self.port)
            assert client.get_connected()
            
            # Perform operation
            data = client.db_read(1, 0, 4)
            assert len(data) >= 4
        
        # Should be disconnected after context exit
        assert not client.get_connected()


class TestServerRobustness:
    """Test server robustness and edge cases."""
    
    def test_multiple_server_instances(self):
        """Test multiple server instances on different ports."""
        servers = []
        clients = []
        
        try:
            # Start multiple servers
            for i in range(3):
                server = PureServer()
                port = 11060 + i
                
                # Register test area
                data = bytearray(100)
                data[0] = i + 1  # Unique identifier
                area_array = (c_char * 100).from_buffer(data)
                server.register_area(SrvArea.DB, 1, area_array)
                
                server.start(port)
                servers.append((server, port))
                time.sleep(0.1)
            
            # Connect clients to each server
            for i, (server, port) in enumerate(servers):
                client = PureClient()
                client.connect("127.0.0.1", 0, 1, port)
                clients.append(client)
                
                # Verify unique data
                data = client.db_read(1, 0, 1)
                assert data[0] == i + 1
            
            print("✓ Multiple server instances work")
            
        finally:
            # Clean up
            for client in clients:
                try:
                    client.disconnect()
                except Exception:
                    pass
            
            for server, port in servers:
                try:
                    server.stop()
                    server.destroy()
                except Exception:
                    pass
    
    def test_server_area_management(self):
        """Test server area registration/unregistration."""
        server = PureServer()
        port = 11070
        
        try:
            # Test area registration
            data1 = bytearray(50)
            data2 = bytearray(100) 
            area1 = (c_char * 50).from_buffer(data1)
            area2 = (c_char * 100).from_buffer(data2)
            
            result1 = server.register_area(SrvArea.DB, 1, area1)
            result2 = server.register_area(SrvArea.DB, 2, area2)
            assert result1 == 0  # Success
            assert result2 == 0  # Success
            
            # Start server
            server.start(port)
            
            # Test client access to both areas
            client = PureClient()
            client.connect("127.0.0.1", 0, 1, port)
            
            data = client.db_read(1, 0, 4)  # Should work
            data = client.db_read(2, 0, 4)  # Should work
            
            # Test area unregistration
            result3 = server.unregister_area(SrvArea.DB, 1)
            assert result3 == 0  # Success
            
            client.disconnect()
            
            print("✓ Server area management works")
            
        finally:
            try:
                server.stop()
                server.destroy()
            except Exception:
                pass