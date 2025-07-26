#!/usr/bin/env python3
"""
Integration example showing both native and library-based S7 clients.
This demonstrates the compatibility between the native Python implementation
and the existing snap7 library wrapper.
"""

import sys
import time

def test_native_client():
    """Test the native Python S7 client"""
    print("=== Native Python S7 Client ===")
    
    try:
        from snap7.low_level.s7_client import S7Client
        from snap7.low_level.s7_protocol import S7Protocol as S7
        
        client = S7Client()
        print("✓ Native client created successfully")
        
        # Test connection (will fail without PLC)
        error = client.connect_to("192.168.1.100", 0, 1, 102)
        if error == 0:
            print("✓ Native client connected to PLC")
            
            # Test basic operations
            buffer = bytearray(4)
            error = client.db_read(1, 0, 4, buffer)
            if error == 0:
                print(f"✓ Native client read data: {buffer.hex()}")
            
            client.disconnect()
            print("✓ Native client disconnected")
        else:
            print(f"⚠ Native client connection failed: {error} (expected without PLC)")
        
        # Test data conversion utilities
        buffer = bytearray(10)
        S7.set_word_at(buffer, 0, 0x1234)
        value = S7.get_word_at(buffer, 0)
        print(f"✓ Native data conversion: 0x1234 -> {hex(value)}")
        
        return True
        
    except Exception as e:
        print(f"✗ Native client error: {e}")
        return False


def test_library_client():
    """Test the standard snap7 library client"""
    print("\n=== Standard Snap7 Library Client ===")
    
    try:
        from snap7.client import Client
        
        client = Client()
        print("✓ Library client created successfully")
        
        # Test connection (will fail without PLC and library)
        try:
            client.connect("192.168.1.100", 0, 1, 102)
            if client.get_connected():
                print("✓ Library client connected to PLC")
                
                # Test basic operations
                data = client.db_read(1, 0, 4)
                print(f"✓ Library client read data: {data.hex()}")
                
                client.disconnect()
                print("✓ Library client disconnected")
            else:
                print("⚠ Library client connection failed (expected without PLC)")
        except Exception as e:
            print(f"⚠ Library client connection error: {e} (expected without native library)")
        
        return True
        
    except ImportError as e:
        print(f"⚠ Library client not available: {e}")
        return False
    except Exception as e:
        print(f"✗ Library client error: {e}")
        return False


def compare_apis():
    """Compare the APIs of both clients"""
    print("\n=== API Comparison ===")
    
    try:
        from snap7.low_level.s7_client import S7Client as NativeClient
        
        native = NativeClient()
        
        print("Native client methods:")
        native_methods = [m for m in dir(native) if not m.startswith('_') and callable(getattr(native, m))]
        for method in sorted(native_methods)[:10]:  # Show first 10
            print(f"  • {method}")
        print(f"  ... and {len(native_methods) - 10} more methods")
        
        print("\nCommon S7 operations (Native API):")
        print("  • client.connect_to(host, rack, slot, port)")
        print("  • client.db_read(db_number, start, size, buffer)")
        print("  • client.db_write(db_number, start, size, buffer)")
        print("  • client.read_int(S7.S7AreaDB, offset, db_number)")
        print("  • client.write_real(S7.S7AreaDB, offset, value, db_number)")
        
        try:
            from snap7.client import Client as LibraryClient
            
            library = LibraryClient()
            print("\nLibrary client methods:")
            library_methods = [m for m in dir(library) if not m.startswith('_') and callable(getattr(library, m))]
            for method in sorted(library_methods)[:10]:  # Show first 10
                print(f"  • {method}")
            print(f"  ... and {len(library_methods) - 10} more methods")
            
            print("\nCommon S7 operations (Library API):")
            print("  • client.connect(host, rack, slot, port)")
            print("  • client.db_read(db_number, start, size)")
            print("  • client.db_write(db_number, start, data)")
            print("  • snap7.util.get_int(data, offset)")
            print("  • snap7.util.set_real(data, offset, value)")
            
        except ImportError:
            print("\nLibrary client not available for comparison")
        
    except Exception as e:
        print(f"Error in API comparison: {e}")


def performance_comparison():
    """Simple performance comparison of data conversion operations"""
    print("\n=== Performance Comparison ===")
    
    try:
        from snap7.low_level.s7_protocol import S7Protocol as S7
        import time
        
        # Test native conversion performance
        buffer = bytearray(1000)
        iterations = 10000
        
        start_time = time.time()
        for i in range(iterations):
            S7.set_word_at(buffer, i % 998, i & 0xFFFF)
            value = S7.get_word_at(buffer, i % 998)
        native_time = time.time() - start_time
        
        print(f"Native conversions: {iterations} operations in {native_time:.3f}s")
        print(f"Rate: {iterations/native_time:.0f} ops/sec")
        
        # Test library conversion if available
        try:
            from snap7.util import get_int, set_int
            
            start_time = time.time()
            for i in range(iterations):
                set_int(buffer, i % 998, i & 0xFFFF)
                value = get_int(buffer, i % 998)
            library_time = time.time() - start_time
            
            print(f"Library conversions: {iterations} operations in {library_time:.3f}s")
            print(f"Rate: {iterations/library_time:.0f} ops/sec")
            
            if library_time > 0:
                ratio = native_time / library_time
                print(f"Performance ratio: {ratio:.2f}x (native vs library)")
            
        except ImportError:
            print("Library utilities not available for performance comparison")
        
    except Exception as e:
        print(f"Error in performance comparison: {e}")


def main():
    """Run all integration tests"""
    print("Snap7 Integration Test - Native vs Library Clients")
    print("=" * 60)
    
    native_ok = test_native_client()
    library_ok = test_library_client()
    
    compare_apis()
    performance_comparison()
    
    print("\n" + "=" * 60)
    print("Integration Test Summary:")
    print(f"  Native Client: {'✓ Working' if native_ok else '✗ Issues'}")
    print(f"  Library Client: {'✓ Working' if library_ok else '⚠ Not Available'}")
    
    print("\nRecommendations:")
    if native_ok and library_ok:
        print("  • Both clients available - choose based on your needs")
        print("  • Native client: No external dependencies, pure Python")
        print("  • Library client: Mature, full-featured, requires native library")
    elif native_ok:
        print("  • Use native client - no external dependencies required")
        print("  • Good for containers, limited environments, development")
    elif library_ok:
        print("  • Use library client - more mature and full-featured")
    else:
        print("  • Check installation and dependencies")
    
    print("\nNext Steps:")
    print("  1. Configure PLC connection parameters")
    print("  2. Test with actual PLC hardware")
    print("  3. Choose client based on requirements")
    print("  4. Implement your S7 communication logic")


if __name__ == "__main__":
    main()