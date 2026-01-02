# TODO: Remaining Protocol Implementations

This document tracks remaining S7 protocol features that could be implemented in the native Python implementation.

## Control Operations - COMPLETED

### compress() - IMPLEMENTED
- Client sends real `PLC_CONTROL` request with PI service "_MSZL"
- Server handles the request and acknowledges

### copy_ram_to_rom() - IMPLEMENTED
- Client sends real `PLC_CONTROL` request with PI service "_MSZL" and file ID "P"
- Server handles the request and acknowledges

---

## Block Transfer - COMPLETED

### upload() - IMPLEMENTED
- Client: Sends START_UPLOAD, UPLOAD, END_UPLOAD sequence
- Server: Returns actual registered DB/block data
- Tested with real protocol roundtrip

### full_upload() - IMPLEMENTED
- Same as upload() but wraps result with MC7 block header
- Returns block data with header and footer

### download() - IMPLEMENTED
- Client: Sends REQUEST_DOWNLOAD, DOWNLOAD_BLOCK, DOWNLOAD_ENDED sequence
- Server: Stores data in registered area
- Tested with real protocol roundtrip

### delete() - IMPLEMENTED
- Client: Sends PLC_CONTROL with PI service "_DELE"
- Server: Handles the request (could unregister area in future)

---

## Authentication (Not Implemented)

### set_session_password()
**Current state**: Client stores password locally without sending protocol
**What to implement**:
- Client: Send `USER_DATA` request with password (group 0x05 = grSecurity)
- Server: Validate password against configured value, track authenticated state per connection
- Store authenticated flag in client handler context
- Default password could be empty or configurable

### clear_session_password()
**Current state**: Client clears local password
**What to implement**:
- Client: Send `USER_DATA` request to clear session
- Server: Clear authenticated flag for connection

---

## Implementation Notes

### Authentication Flow (Future Implementation)
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

### Server Password Configuration (Future)
Could add to Server constructor:
```python
server = Server(password="secret")  # Or None for no auth required
```

---

## References

- Snap7 C source: `src/core/s7_client.cpp` (Cli_Upload, Cli_Download)
- S7 protocol docs: Function codes and USER_DATA groups
- Existing implementations: `list_blocks()`, `read_szl()` for USER_DATA patterns
