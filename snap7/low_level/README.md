# Native Python S7 Client

This directory contains a native Python implementation of an S7 protocol client, similar to the Sharp7 project but written entirely in Python without dependencies on external native libraries.

## Overview

The native Python S7 client provides a pure Python implementation for communicating with Siemens S7 PLCs. It's designed to be similar to the Sharp7 C# library, offering the same functionality but in Python.

## Components

### Core Classes

- **S7Client** (`s7_client.py`) - Main client class for connecting to S7 PLCs
- **S7Protocol** (`s7_protocol.py`) - Protocol definitions, constants, and data conversion utilities
- **S7Socket** (`s7_socket.py`) - TCP socket handling and communication
- **S7Server** (`s7_server.py`) - S7 server implementation for PLC simulation
- **S7Partner** (`s7_partner.py`) - S7 partner implementation for peer-to-peer communication
- **S7IsoTcp** (`s7_isotcp.py`) - ISO TCP protocol layer (partial implementation)

### Key Features

1. **Pure Python** - No external native library dependencies
2. **Sharp7-compatible API** - Similar method names and functionality to Sharp7
3. **Complete Data Type Support** - All S7 data types with conversion utilities
4. **Memory Area Access** - Support for DB, M, I, Q, C, T memory areas
5. **Connection Management** - Proper connection establishment and error handling
6. **Convenience Methods** - Type-safe methods for reading/writing specific data types

## Usage Examples

### Basic Connection and Reading

```python
from snap7.low_level.s7_client import S7Client

# Create client
client = S7Client()

# Connect to PLC
error = client.connect_to("192.168.1.100", rack=0, slot=1, port=102)
if error == 0:
    print("Connected successfully!")
    
    # Read from DB1, 10 bytes starting at offset 0
    buffer = bytearray(10)
    error = client.db_read(1, 0, 10, buffer)
    if error == 0:
        print(f"Data: {buffer.hex()}")
    
    client.disconnect()
else:
    print(f"Connection failed: {error}")
```

### Using Convenience Methods

```python
# Read different data types
error, bool_value = client.read_bool(S7.S7AreaDB, 0, 0, db_number=1)  # Read bit 0 of byte 0
error, int_value = client.read_int(S7.S7AreaDB, 2, db_number=1)        # Read INT at offset 2
error, real_value = client.read_real(S7.S7AreaDB, 4, db_number=1)      # Read REAL at offset 4

# Write different data types
client.write_bool(S7.S7AreaDB, 0, 0, True, db_number=1)               # Write bit 0 of byte 0
client.write_int(S7.S7AreaDB, 2, 1234, db_number=1)                   # Write INT at offset 2
client.write_real(S7.S7AreaDB, 4, 3.14159, db_number=1)               # Write REAL at offset 4
```

### Working with Different Memory Areas

```python
from snap7.low_level.s7_protocol import S7Protocol as S7

# Read from different memory areas
buffer = bytearray(10)

# Data Block (DB)
client.db_read(1, 0, 10, buffer)

# Merker/Memory (M)
client.mb_read(0, 10, buffer)

# Inputs (I) 
client.eb_read(0, 10, buffer)

# Outputs (Q)
client.ab_read(0, 10, buffer)

# Using read_area directly
client.read_area(S7.S7AreaDB, start=0, amount=10, word_len=S7.S7WLByte, buffer=buffer, db_number=1)
```

### Data Conversion Utilities

```python
from snap7.low_level.s7_protocol import S7Protocol as S7

buffer = bytearray(20)

# Set and get different data types
S7.set_word_at(buffer, 0, 0x1234)      # Set 16-bit word
value = S7.get_word_at(buffer, 0)      # Get 16-bit word

S7.SetIntAt(buffer, 2, -1234)          # Set signed integer
value = S7.get_int_at(buffer, 2)       # Get signed integer

S7.SetRealAt(buffer, 4, 3.14159)       # Set float
value = S7.GetRealAt(buffer, 4)        # Get float

S7.SetStringAt(buffer, 8, 10, "Hello") # Set string
value = S7.GetStringAt(buffer, 8)      # Get string

# Bit operations
S7.SetBitAt(buffer, 18, 3, True)       # Set bit 3 of byte 18
bit = S7.GetBitAt(buffer, 18, 3)       # Get bit 3 of byte 18
```

## API Reference

### S7Client Methods

#### Connection Methods
- `connect_to(host, rack, slot, port)` - Connect to PLC
- `connect()` - Connect using pre-set parameters
- `disconnect()` - Disconnect from PLC
- `connected` - Property indicating connection status

#### Data Block Operations
- `db_read(db_number, start, size, buffer)` - Read from data block
- `db_write(db_number, start, size, buffer)` - Write to data block

#### Memory Area Operations
- `mb_read(start, size, buffer)` - Read from merker area
- `mb_write(start, size, buffer)` - Write to merker area
- `eb_read(start, size, buffer)` - Read from input area
- `eb_write(start, size, buffer)` - Write to input area
- `ab_read(start, size, buffer)` - Read from output area
- `ab_write(start, size, buffer)` - Write to output area

#### Generic Operations
- `read_area(area, start, amount, word_len, buffer, db_number)` - Generic read
- `write_area(area, start, amount, word_len, buffer, db_number)` - Generic write

#### Convenience Methods
- `read_bool(area, start, bit, db_number)` - Read boolean
- `write_bool(area, start, bit, value, db_number)` - Write boolean
- `read_int(area, start, db_number)` - Read 16-bit signed integer
- `write_int(area, start, value, db_number)` - Write 16-bit signed integer
- `read_word(area, start, db_number)` - Read 16-bit unsigned integer
- `write_word(area, start, value, db_number)` - Write 16-bit unsigned integer
- `read_dword(area, start, db_number)` - Read 32-bit unsigned integer
- `write_dword(area, start, value, db_number)` - Write 32-bit unsigned integer
- `read_real(area, start, db_number)` - Read 32-bit float
- `write_real(area, start, value, db_number)` - Write 32-bit float
- `read_string(area, start, max_len, db_number)` - Read string
- `write_string(area, start, value, max_len, db_number)` - Write string

#### Information Methods
- `get_cpu_info(cpu_info)` - Get CPU information
- `get_cp_info(cp_info)` - Get CP information
- `get_order_code(order_code)` - Get order code
- `get_protection(protection)` - Get protection status
- `get_cpu_state(status_ref)` - Get CPU state

#### Utility Methods
- `get_last_error()` - Get last error code
- `get_exec_time()` - Get execution time of last operation
- `set_session_password(password)` - Set session password
- `clear_session_password()` - Clear session password

### Error Codes

Common error codes defined in S7Protocol:

- `errTCPNotConnected` (0x9) - TCP not connected
- `errTCPConnectionFailed` (0x3) - TCP connection failed
- `errIsoInvalidPDU` (0x30000) - Invalid ISO PDU
- `errCliAddressOutOfRange` (0x900000) - Address out of range
- `errCliInvalidWordLen` (0x500000) - Invalid word length
- `errCliNegotiatingPDU` (0x100000) - PDU negotiation failed

### Memory Areas

- `S7.S7AreaDB` (0x84) - Data Blocks
- `S7.S7AreaMK` (0x83) - Merker/Memory
- `S7.S7AreaPE` (0x81) - Process Input
- `S7.S7AreaPA` (0x82) - Process Output
- `S7.S7AreaCT` (0x1C) - Counters
- `S7.S7AreaTM` (0x1D) - Timers

### Word Lengths

- `S7.S7WLBit` (0x01) - Bit
- `S7.S7WLByte` (0x02) - Byte
- `S7.S7WLChar` (0x03) - Character
- `S7.S7WLWord` (0x04) - Word (16-bit)
- `S7.S7WLInt` (0x05) - Integer (16-bit)
- `S7.S7WLDWord` (0x06) - Double Word (32-bit)
- `S7.S7WLDInt` (0x07) - Double Integer (32-bit)
- `S7.S7WLReal` (0x08) - Real (32-bit float)
- `S7.S7WLCounter` (0x1C) - Counter
- `S7.S7WLTimer` (0x1D) - Timer

## Testing

Run the test suite:

```bash
python test_native_client.py
```

Run the examples:

```bash
python examples_native_client.py
```

## Limitations

1. **ISO TCP Layer** - The ISO TCP implementation is basic and may not handle all edge cases
2. **Server Implementation** - The S7Server is a simple test server, not a full PLC simulator
3. **Multi-variable Operations** - Multi-variable read/write operations are not yet implemented
4. **Security** - Limited security features compared to modern S7 implementations

## Compatibility

This implementation aims to be compatible with:
- Sharp7 C# library API
- Standard S7 protocol as used by Siemens PLCs
- TIA Portal and Step 7 programming environments

## Development

To extend the implementation:

1. **Add Protocol Features** - Implement missing S7 protocol features in S7Protocol
2. **Improve ISO Layer** - Complete the ISO TCP implementation in S7IsoTcp
3. **Add Security** - Implement S7 security features
4. **Optimize Performance** - Add connection pooling, async operations
5. **Add Testing** - Create tests with real PLC hardware

### Using S7Server

```python
from snap7.low_level.s7_server import S7Server

# Create and start server
server = S7Server()

# Register a data block
db_data = bytearray(1024)
server.register_area(0x84, 1, db_data)  # DB1 with 1024 bytes

# Start server on port 102
error = server.start("0.0.0.0", 102)
if error == 0:
    print("Server started successfully!")
    
    # Get server status
    server_status, cpu_status, clients_count = server.get_status()
    print(f"Server Status: {server_status}, CPU: {cpu_status}, Clients: {clients_count}")
    
    # Server runs in background thread
    # ... do other work ...
    
    # Stop server
    server.stop()
```

### Using S7Partner

```python
from snap7.low_level.s7_partner import S7Partner

# Create active partner (initiates connection)
partner = S7Partner(active=True)

# Connect to remote partner
error = partner.start_to("0.0.0.0", "192.168.1.100")
if error == 0:
    print("Connected to partner!")
    
    # Send data synchronously
    partner.send_buffer = bytearray(b"Hello Partner!")
    partner.send_size = 14
    error = partner.b_send()
    
    # Receive data synchronously
    error = partner.b_recv()
    if error == 0:
        print(f"Received: {partner.recv_buffer[:partner.recv_size]}")
    
    # Or send asynchronously
    partner.as_b_send()
    status, result = partner.check_as_b_send_completion()
    
    partner.stop()
```

## Contributing

When contributing to the native S7 client:

1. Keep changes minimal and focused
2. Maintain compatibility with Sharp7 API
3. Add tests for new functionality
4. Update documentation
5. Follow existing code style and patterns