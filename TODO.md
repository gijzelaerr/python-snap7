# TODO: Remaining Protocol Implementations

This document tracks remaining S7 protocol features that could be implemented in the native Python implementation.

## Control Operations (Easy)

### compress()
**Current state**: Client returns success without sending protocol
**What to implement**:
- Client: Send real `PLC_CONTROL` request with compress control code
- Server: Acknowledge request (emulator doesn't need actual memory compaction)
- Protocol: Function code 0x28 (PLC_CONTROL) with "compress" parameter

### copy_ram_to_rom()
**Current state**: Client returns success without sending protocol
**What to implement**:
- Client: Send real `PLC_CONTROL` request with copy control code
- Server: Acknowledge request (could optionally persist areas to disk)
- Protocol: Function code 0x28 (PLC_CONTROL) with "copy" parameter

---

## Authentication (Medium)

### set_session_password()
**Current state**: Client returns success without validation
**What to implement**:
- Client: Send `USER_DATA` request with password (group 0x05 = grSecurity)
- Server: Validate password against configured value, track authenticated state per connection
- Store authenticated flag in client handler context
- Default password could be empty or configurable

### clear_session_password()
**Current state**: Client returns success
**What to implement**:
- Client: Send `USER_DATA` request to clear session
- Server: Clear authenticated flag for connection

---

## Block Transfer (Medium)

### upload() - Transfer block FROM PLC to client
**Current state**: Skipped in tests ("Not implemented")
**What to implement**:
- Client: Send upload request specifying block type and number
- Server: Return actual registered DB/block data
- Handle multi-packet transfers for large blocks
- Protocol sequence:
  1. Start upload request
  2. Server acknowledges with upload ID
  3. Client requests data packets
  4. Server sends block data in chunks
  5. End upload

### full_upload()
**Current state**: Returns dummy data
**What to implement**:
- Same as upload() but includes block header (MC7 format)
- Return block metadata (size, author, timestamp, etc.)

### download() - Transfer block TO PLC from client
**Current state**: Skipped in tests ("Not implemented")
**What to implement**:
- Client: Send download request with block data
- Server: Store data in registered area (create if needed)
- Handle multi-packet transfers for large blocks
- Protocol sequence:
  1. Request download permission
  2. Server acknowledges
  3. Client sends block data in chunks
  4. End download
  5. Server confirms

### delete()
**Current state**: Returns success without action
**What to implement**:
- Client: Send delete block request
- Server: Unregister the specified area
- Could require authentication

---

## Implementation Notes

### Authentication Flow
```
Client                          Server
  |-- set_session_password -->    |
  |    (USER_DATA grSecurity)     |
  |                               | (validate password)
  |<-- success/error response ----|
  |                               |
  |-- upload() request -------->  |
  |    (now allowed)              |
```

### Block Transfer Protocol
The S7 block transfer uses a multi-step handshake:
- Uses function codes 0x1D (start upload), 0x1E (upload), 0x1F (end upload)
- For download: 0x1A (request download), 0x1B (download block), 0x1C (end download)
- Each packet contains sequence numbers for reassembly

### Server Password Configuration
Could add to Server constructor:
```python
server = Server(password="secret")  # Or None for no auth required
```

---

## Priority Order

1. **compress / copy_ram_to_rom** - Easy wins, just need PLC_CONTROL protocol
2. **Authentication** - Enables testing of protected operations
3. **upload / download** - Full block transfer capability

---

## References

- Snap7 C source: `src/core/s7_client.cpp` (Cli_Upload, Cli_Download)
- S7 protocol docs: Function codes and USER_DATA groups
- Existing implementations: `list_blocks()`, `read_szl()` for USER_DATA patterns
