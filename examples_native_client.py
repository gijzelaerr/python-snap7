#!/usr/bin/env python3
"""
Example usage of the native Python S7 client implementation.
This demonstrates how to use the low_level S7Client similar to Sharp7.
"""

import time
from snap7.low_level.s7_client import S7Client
from snap7.low_level.s7_protocol import S7Protocol as S7
from snap7.type import S7CpuInfo, S7CpInfo, S7OrderCode, S7Protection


def example_basic_usage():
    """Basic usage example"""
    print("=== Basic Usage Example ===")
    
    # Create client
    client = S7Client()
    
    # Connection parameters
    host = "192.168.1.100"  # Replace with your PLC IP
    rack = 0
    slot = 1
    port = 102
    
    print(f"Connecting to {host}:{port}, rack={rack}, slot={slot}...")
    
    # Connect to PLC
    error = client.connect_to(host, rack, slot, port)
    
    if error != 0:
        print(f"Connection failed with error: {error}")
        print("This is expected if no PLC is available at the specified address")
        return
    
    print("✓ Connected successfully!")
    
    try:
        # Get PLC information
        cpu_info = S7CpuInfo()
        error = client.get_cpu_info(cpu_info)
        if error == 0:
            print(f"CPU: {cpu_info.ModuleName}")
            print(f"Serial: {cpu_info.SerialNumber}")
        
        # Read from DB1, starting at byte 0, 10 bytes
        print("\nReading from DB1...")
        buffer = bytearray(10)
        error = client.db_read(1, 0, 10, buffer)
        if error == 0:
            print(f"Read data: {buffer.hex()}")
        else:
            print(f"Read failed with error: {error}")
        
        # Write to DB1
        print("\nWriting to DB1...")
        write_data = bytearray([0x11, 0x22, 0x33, 0x44])
        error = client.db_write(1, 0, 4, write_data)
        if error == 0:
            print("✓ Write successful")
        else:
            print(f"Write failed with error: {error}")
            
    finally:
        # Always disconnect
        client.disconnect()
        print("✓ Disconnected")


def example_data_types():
    """Example of reading/writing different data types"""
    print("\n=== Data Types Example ===")
    
    client = S7Client()
    
    # Note: This example won't work without a real PLC connection
    # but shows the API usage
    
    print("Example API calls for different data types:")
    
    # Boolean operations
    print("• Boolean: client.read_bool(S7.S7AreaDB, 0, 0, db_number=1)")
    print("• Boolean: client.write_bool(S7.S7AreaDB, 0, 0, True, db_number=1)")
    
    # Integer operations  
    print("• Int16: client.read_int(S7.S7AreaDB, 2, db_number=1)")
    print("• Int16: client.write_int(S7.S7AreaDB, 2, 1234, db_number=1)")
    
    # Word operations
    print("• Word: client.read_word(S7.S7AreaDB, 4, db_number=1)")
    print("• Word: client.write_word(S7.S7AreaDB, 4, 0xABCD, db_number=1)")
    
    # DWord operations
    print("• DWord: client.read_dword(S7.S7AreaDB, 6, db_number=1)")
    print("• DWord: client.write_dword(S7.S7AreaDB, 6, 0x12345678, db_number=1)")
    
    # Real operations
    print("• Real: client.read_real(S7.S7AreaDB, 10, db_number=1)")
    print("• Real: client.write_real(S7.S7AreaDB, 10, 3.14159, db_number=1)")
    
    # String operations
    print("• String: client.read_string(S7.S7AreaDB, 14, 20, db_number=1)")
    print("• String: client.write_string(S7.S7AreaDB, 14, 'Hello PLC', 20, db_number=1)")


def example_memory_areas():
    """Example of working with different memory areas"""
    print("\n=== Memory Areas Example ===")
    
    client = S7Client()
    
    print("Different memory areas that can be accessed:")
    print("• Data Blocks (DB): S7.S7AreaDB")
    print("• Merker/Memory (M): S7.S7AreaMK") 
    print("• Inputs (I): S7.S7AreaPE")
    print("• Outputs (Q): S7.S7AreaPA")
    print("• Counters (C): S7.S7AreaCT")
    print("• Timers (T): S7.S7AreaTM")
    
    print("\nExample usage:")
    print("• Read 10 bytes from Merker area: client.mb_read(0, 10, buffer)")
    print("• Read 8 bytes from Input area: client.eb_read(0, 8, buffer)")
    print("• Read 4 bytes from Output area: client.ab_read(0, 4, buffer)")


def example_protocol_helpers():
    """Example of using S7Protocol helper functions"""
    print("\n=== Protocol Helpers Example ===")
    
    # Create a buffer for demonstration
    buffer = bytearray(20)
    
    print("S7Protocol provides many helper functions for data conversion:")
    
    # Word operations
    S7.set_word_at(buffer, 0, 0x1234)
    value = S7.get_word_at(buffer, 0)
    print(f"• Word: Set 0x1234, Read {hex(value)}")
    
    # Integer operations
    S7.SetIntAt(buffer, 2, -1234)
    value = S7.get_int_at(buffer, 2)
    print(f"• Int: Set -1234, Read {value}")
    
    # Real operations
    S7.SetRealAt(buffer, 4, 3.14159)
    value = S7.GetRealAt(buffer, 4)
    print(f"• Real: Set 3.14159, Read {value:.5f}")
    
    # String operations
    S7.SetStringAt(buffer, 8, 10, "Hello")
    value = S7.GetStringAt(buffer, 8)
    print(f"• String: Set 'Hello', Read '{value}'")
    
    # Bit operations
    S7.SetBitAt(buffer, 18, 3, True)  # Set bit 3 of byte 18
    bit_value = S7.GetBitAt(buffer, 18, 3)
    print(f"• Bit: Set bit 3 to True, Read {bit_value}")


def example_error_handling():
    """Example of error handling"""
    print("\n=== Error Handling Example ===")
    
    client = S7Client()
    
    # Try to read without connection
    buffer = bytearray(4)
    error = client.db_read(1, 0, 4, buffer)
    
    print(f"Read without connection - Error code: {error}")
    print(f"Error code {error} = {hex(error)} (errTCPNotConnected)")
    
    # Check last error
    last_error = client.get_last_error()
    print(f"Last error: {last_error}")
    
    print("\nCommon error codes:")
    print(f"• TCP Not Connected: {S7.errTCPNotConnected} ({hex(S7.errTCPNotConnected)})")
    print(f"• TCP Connection Failed: {S7.errTCPConnectionFailed} ({hex(S7.errTCPConnectionFailed)})")
    print(f"• Invalid PDU: {S7.errIsoInvalidPDU} ({hex(S7.errIsoInvalidPDU)})")
    print(f"• Address Out of Range: {S7.errCliAddressOutOfRange} ({hex(S7.errCliAddressOutOfRange)})")


def main():
    """Run all examples"""
    print("Native Python S7 Client Examples")
    print("=" * 40)
    
    example_basic_usage()
    example_data_types() 
    example_memory_areas()
    example_protocol_helpers()
    example_error_handling()
    
    print("\n" + "=" * 40)
    print("Examples completed!")
    print("\nTo use with a real PLC:")
    print("1. Update the host IP address in example_basic_usage()")
    print("2. Ensure the PLC is accessible on the network")
    print("3. Configure rack and slot parameters for your PLC")
    print("4. Run the examples with a connected PLC")


if __name__ == "__main__":
    main()