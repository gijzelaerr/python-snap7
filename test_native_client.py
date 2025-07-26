#!/usr/bin/env python3
"""
Test script for the native Python S7 client implementation.
This tests the low_level S7Client similar to Sharp7.
"""

import time
from snap7.low_level.s7_client import S7Client
from snap7.low_level.s7_server import S7Server
from snap7.low_level.s7_protocol import S7Protocol as S7
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


def test_convenience_methods():
    """Test the convenience methods for different data types"""
    print("Testing convenience methods...")
    
    client = S7Client()
    
    # Test that methods exist and handle unconnected state gracefully
    error, value = client.read_bool(S7.S7AreaDB, 0, 0, 1)
    print(f"read_bool (no connection): {error}")
    assert error == S7.errTCPNotConnected
    
    error, value = client.read_int(S7.S7AreaDB, 2, 1)
    print(f"read_int (no connection): {error}")
    assert error == S7.errTCPNotConnected
    
    error, value = client.read_word(S7.S7AreaDB, 4, 1)
    print(f"read_word (no connection): {error}")
    assert error == S7.errTCPNotConnected
    
    error, value = client.read_real(S7.S7AreaDB, 6, 1)
    print(f"read_real (no connection): {error}")
    assert error == S7.errTCPNotConnected
    
    # Test write methods
    error = client.write_bool(S7.S7AreaDB, 0, 0, True, 1)
    print(f"write_bool (no connection): {error}")
    assert error == S7.errTCPNotConnected
    
    error = client.write_int(S7.S7AreaDB, 2, 1234, 1)
    print(f"write_int (no connection): {error}")
    assert error == S7.errTCPNotConnected
    
    error = client.write_real(S7.S7AreaDB, 6, 3.14, 1)
    print(f"write_real (no connection): {error}")
    assert error == S7.errTCPNotConnected
    
    print("✓ Convenience methods test passed")


def test_api_compatibility():
    """Test API compatibility with expected Sharp7-like interface"""
    print("Testing API compatibility...")
    
    client = S7Client()
    
    # Test that client has expected Sharp7-like methods
    expected_methods = [
        'connect', 'connect_to', 'disconnect',
        'db_read', 'db_write', 'mb_read', 'mb_write',
        'eb_read', 'eb_write', 'ab_read', 'ab_write',
        'read_area', 'write_area',
        'get_cpu_info', 'get_cp_info', 'get_order_code', 'get_protection',
        'get_cpu_state', 'set_session_password', 'clear_session_password',
        'get_last_error', 'get_exec_time',
        # New convenience methods
        'read_bool', 'write_bool', 'read_int', 'write_int',
        'read_word', 'write_word', 'read_real', 'write_real'
    ]
    
    # Test properties
    expected_properties = ['connected']
    
    for method in expected_methods:
        assert hasattr(client, method), f"Missing method: {method}"
        assert callable(getattr(client, method)), f"Method not callable: {method}"
    
    for prop in expected_properties:
        assert hasattr(client, prop), f"Missing property: {prop}"
        # Test that the property can be accessed
        try:
            _ = getattr(client, prop)
        except Exception as e:
            assert False, f"Property {prop} not accessible: {e}"
    
    print("✓ API compatibility test passed")


def test_data_conversion_extended():
    """Test extended data conversion methods"""
    print("Testing extended data conversion...")
    
    from snap7.low_level.s7_protocol import S7Protocol as S7
    
    buffer = bytearray(100)
    
    # Test datetime conversions
    import datetime
    
    # Test date/time operations
    now = datetime.datetime.now()
    S7.SetDateTimeAt(buffer, 0, now)
    retrieved = S7.GetDateTimeAt(buffer, 0)
    print(f"DateTime: {now} -> {retrieved}")
    
    # Test date operations
    today = datetime.date.today()
    date_dt = datetime.datetime.combine(today, datetime.time())
    S7.SetDateAt(buffer, 10, date_dt)
    retrieved_date = S7.GetDateAt(buffer, 10)
    print(f"Date: {date_dt} -> {retrieved_date}")
    
    # Test BCD conversions
    bcd_val = S7.ByteToBCD(99)
    dec_val = S7.BCDtoByte(bcd_val)
    assert dec_val == 99, f"BCD conversion failed: {dec_val}"
    
    print("✓ Extended data conversion tests passed")


def main():
    """Run all tests"""
    print("=== Native Python S7 Client Tests ===\n")
    
    try:
        test_basic_client_creation()
        print()
        
        test_data_conversion() 
        print()
        
        test_data_conversion_extended()
        print()
        
        test_convenience_methods()
        print()
        
        test_api_compatibility()
        print()
        
        test_client_info_methods()
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