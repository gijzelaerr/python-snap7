"""
S7CommPlus protocol implementation for S7-1200/1500 PLCs.

S7CommPlus (protocol ID 0x72) is the successor to S7comm (protocol ID 0x32),
used by Siemens S7-1200 (firmware >= V4.0) and S7-1500 PLCs for full
engineering access (program download/upload, symbolic addressing, etc.).

Supported PLC / firmware targets::

    V1: S7-1200 FW V4.0+          (simple session handshake)
    V2: S7-1200/1500 older FW      (session authentication)
    V3: S7-1200/1500 pre-TIA V17   (public-key key exchange)
    V3 + TLS: TIA Portal V17+      (TLS 1.3 with per-device certs)

Protocol stack::

    +-------------------------------+
    |  S7CommPlus (Protocol ID 0x72)|
    +-------------------------------+
    |  TLS 1.3 (optional, V17+)    |
    +-------------------------------+
    |  COTP (ISO 8073)              |
    +-------------------------------+
    |  TPKT (RFC 1006)              |
    +-------------------------------+
    |  TCP (port 102)               |
    +-------------------------------+

The wire protocol (VLQ encoding, data types, function codes, object model)
is the same across all versions -- only the session authentication differs.

Status: V1 connection functional, V2 (TLS + IntegrityId) scaffolding complete.

Reference implementation:
    https://github.com/thomas-v2/S7CommPlusDriver (C#, LGPL-3.0)
"""
