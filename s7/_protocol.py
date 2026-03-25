"""Protocol enum for unified S7 client."""

from enum import Enum


class Protocol(Enum):
    """S7 communication protocol selection.

    Used to control protocol auto-discovery in the unified client.

    Attributes:
        AUTO: Try S7CommPlus first, fall back to legacy S7 if unsupported.
        LEGACY: Use legacy S7 protocol only (S7-300/400, basic S7-1200/1500).
        S7COMMPLUS: Use S7CommPlus protocol only (S7-1200/1500 with full access).
    """

    AUTO = "auto"
    LEGACY = "legacy"
    S7COMMPLUS = "s7commplus"
