#!/usr/bin/env python3
"""
Simple example showing how to use the native S7 client from the main snap7 module.
"""

import snap7

def main():
    print("Testing native S7 client import from main module...")
    
    # Check if native client is available
    if hasattr(snap7, 'NativeClient'):
        print("✓ Native client available from snap7.NativeClient")
        
        # Create native client
        client = snap7.NativeClient()
        print("✓ Native client created successfully")
        
        # Test basic functionality
        print(f"Connected: {client.connected}")
        print(f"Last error: {client.get_last_error()}")
        
        # Show available methods
        methods = [m for m in dir(client) if not m.startswith('_')]
        print(f"Available methods: {len(methods)}")
        print("Key methods:", ', '.join([
            'connect_to', 'db_read', 'db_write', 'read_int', 'write_real'
        ]))
        
    else:
        print("✗ Native client not available")
    
    # Also test direct import
    try:
        from snap7.low_level.s7_client import S7Client
        from snap7.low_level.s7_protocol import S7Protocol as S7
        
        print("\n✓ Direct import also works:")
        print("  from snap7.low_level.s7_client import S7Client")
        print("  from snap7.low_level.s7_protocol import S7Protocol as S7")
        
        client = S7Client()
        print("✓ Direct import client created")
        
    except ImportError as e:
        print(f"✗ Direct import failed: {e}")

if __name__ == "__main__":
    main()