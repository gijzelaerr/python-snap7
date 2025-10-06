"""
S7 Protocol Constants.
Used by ISO TCP and other low-level components.
"""


class S7Consts:
    """Constants for S7 protocol implementation."""

    # ISO TCP constants
    isoTcpPort = 102  # Standard S7 port
    MaxIsoFragments = 64  # Maximum number of ISO fragments
    IsoPayload_Size = 4096  # ISO telegram buffer size
    noError = 0  # No error constant
