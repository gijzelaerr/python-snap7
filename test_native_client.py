#!/usr/bin/env python3
"""
Test script for the native Python S7 client implementation.
This tests the low_level S7Client similar to Sharp7.
"""

import time
from snap7.low_level.s7_client import S7Client
from snap7.low_level.s7_server import S7Server
from snap7.type import S7CpuInfo, S7CpInfo, S7OrderCode, S7Protection


def test_basic_client_creation():
    """Test basic client creation and methods"""
    print("Testing basic client creation...")
    client = S7Client()
    
    # Test basic properties
    assert not client.connected, "Client should not be connected initially"
    assert client.get_last_error() == 0, "Initial error should be 0"
    
    print("✓ Basic client creation test passed")


def test_server_client_connection():
    """Test connection between server and client"""
    print("Testing server-client connection...")
    
    # For now, test the TCP connection part only since ISO layer needs more work
    # Start server
    server = S7Server()
    server.start("127.0.0.1", 1102)
    time.sleep(0.2)  # Give server time to start
    
    # Test TCP connect
    client = S7Client()
    client._address_PLC = "127.0.0.1"
    client._port_PLC = 1102
    
    error = client.tcp_connect()
    if error == 0:
        print("✓ TCP connection successful")
        tcp_connected = client.socket.connected
        print(f"Socket connected: {tcp_connected}")
        
        # Test disconnection
        client.disconnect()
        print("✓ TCP disconnection successful")
    else:
        print(f"⚠ TCP connection failed with error: {error}")
    
    # Test full S7 connection (will likely fail due to simple server)
    client2 = S7Client()
    error2 = client2.connect_to("127.0.0.1", 0, 2, 1102)
    if error2 == 0:
        print("✓ Full S7 connection successful")
        client2.disconnect()
    else:
        print(f"⚠ Full S7 connection failed with error: {error2} (expected with simple test server)")
    
    # Stop server
    server.stop()
    print("✓ Server-client connection test completed")


def test_data_conversion():
    """Test S7Protocol data conversion methods"""
    print("Testing data conversion methods...")
    
    from snap7.low_level.s7_protocol import S7Protocol as S7
    
    # Test basic data conversions
    buffer = bytearray(10)
    
    # Test word operations
    S7.set_word_at(buffer, 0, 0x1234)
    value = S7.get_word_at(buffer, 0)
    assert value == 0x1234, f"Word conversion failed: got {value}, expected 0x1234"
    
    # Test int operations
    S7.SetIntAt(buffer, 2, -1234)
    value = S7.get_int_at(buffer, 2)
    assert value == -1234, f"Int conversion failed: got {value}, expected -1234"
    
    # Test real operations
    S7.SetRealAt(buffer, 4, 3.14159)
    value = S7.GetRealAt(buffer, 4)
    assert abs(value - 3.14159) < 0.001, f"Real conversion failed: got {value}, expected 3.14159"
    
    print("✓ Data conversion tests passed")


def test_client_info_methods():
    """Test client info methods without connection"""
    print("Testing client info methods...")
    
    client = S7Client()
    
    # These methods require a connection, so they should fail gracefully
    cpu_info = S7CpuInfo()
    error = client.get_cpu_info(cpu_info)
    print(f"get_cpu_info (no connection): {error}")
    
    cp_info = S7CpInfo()
    error = client.get_cp_info(cp_info)
    print(f"get_cp_info (no connection): {error}")
    
    order_code = S7OrderCode()
    error = client.get_order_code(order_code)
    print(f"get_order_code (no connection): {error}")
    
    protection = S7Protection()
    error = client.get_protection(protection)
    print(f"get_protection (no connection): {error}")
    
    print("✓ Client info methods test completed")


def test_read_write_operations():
    """Test read/write operations without connection"""
    print("Testing read/write operations...")
    
    client = S7Client()
    
    # Test DB read/write
    buffer = bytearray(10)
    error = client.db_read(1, 0, 10, buffer)
    print(f"db_read (no connection): {error}")
    
    error = client.db_write(1, 0, 10, buffer)
    print(f"db_write (no connection): {error}")
    
    # Test other area operations
    error = client.mb_read(0, 10, buffer)
    print(f"mb_read (no connection): {error}")
    
    error = client.eb_read(0, 10, buffer)
    print(f"eb_read (no connection): {error}")
    
    error = client.ab_read(0, 10, buffer)
    print(f"ab_read (no connection): {error}")
    
    print("✓ Read/write operations test completed")


def main():
    """Run all tests"""
    print("=== Native Python S7 Client Tests ===\n")
    
    try:
        test_basic_client_creation()
        print()
        
        test_data_conversion() 
        print()
        
        test_client_info_methods()
        print()
        
        test_read_write_operations()
        print()
        
        test_server_client_connection()
        print()
        
        print("=== All tests completed! ===")
        
    except Exception as e:
        print(f"Test failed with exception: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())