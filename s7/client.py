"""Unified S7 client with protocol auto-discovery.

Provides a single client that automatically selects the best protocol
(S7CommPlus or legacy S7) for communicating with Siemens S7 PLCs.

Usage::

    from s7 import Client

    client = Client()
    client.connect("192.168.1.10", 0, 1)
    data = client.db_read(1, 0, 4)
"""

import logging
from typing import Any, Optional

from snap7.client import Client as LegacyClient

from ._protocol import Protocol
from ._s7commplus_client import S7CommPlusClient

logger = logging.getLogger(__name__)


class Client:
    """Unified S7 client with protocol auto-discovery.

    Automatically selects the best protocol for the target PLC:
    - S7CommPlus for S7-1200/1500 PLCs with full data operations
    - Legacy S7 for S7-300/400 or when S7CommPlus is unavailable

    Methods not explicitly defined are delegated to the underlying
    legacy client via ``__getattr__``.

    Example::

        from s7 import Client

        client = Client()
        client.connect("192.168.1.10", 0, 1)
        data = client.db_read(1, 0, 4)
        print(client.protocol)
    """

    def __init__(self) -> None:
        self._legacy: Optional[LegacyClient] = None
        self._plus: Optional[S7CommPlusClient] = None
        self._protocol: Protocol = Protocol.AUTO
        self._host: str = ""
        self._port: int = 102
        self._rack: int = 0
        self._slot: int = 1

    @property
    def protocol(self) -> Protocol:
        """The protocol currently in use for DB operations."""
        return self._protocol

    @property
    def connected(self) -> bool:
        """Whether the client is connected to a PLC."""
        if self._legacy is not None and self._legacy.connected:
            return True
        if self._plus is not None and self._plus.connected:
            return True
        return False

    def connect(
        self,
        address: str,
        rack: int = 0,
        slot: int = 1,
        tcp_port: int = 102,
        *,
        protocol: Protocol = Protocol.AUTO,
        use_tls: bool = False,
        tls_cert: Optional[str] = None,
        tls_key: Optional[str] = None,
        tls_ca: Optional[str] = None,
        password: Optional[str] = None,
    ) -> "Client":
        """Connect to an S7 PLC.

        Args:
            address: PLC IP address or hostname.
            rack: PLC rack number.
            slot: PLC slot number.
            tcp_port: TCP port (default 102).
            protocol: Protocol selection. AUTO tries S7CommPlus first,
                then falls back to legacy S7.
            use_tls: Whether to activate TLS (required for V2+).
            tls_cert: Path to client TLS certificate (PEM).
            tls_key: Path to client private key (PEM).
            tls_ca: Path to CA certificate for PLC verification (PEM).
            password: PLC password for legitimation (V2+ with TLS).

        Returns:
            self, for method chaining.
        """
        self._host = address
        self._port = tcp_port
        self._rack = rack
        self._slot = slot

        if protocol in (Protocol.AUTO, Protocol.S7COMMPLUS):
            if self._try_s7commplus(
                address,
                tcp_port,
                rack,
                slot,
                use_tls=use_tls,
                tls_cert=tls_cert,
                tls_key=tls_key,
                tls_ca=tls_ca,
                password=password,
            ):
                self._protocol = Protocol.S7COMMPLUS
                logger.info(f"Connected to {address}:{tcp_port} using S7CommPlus")
            else:
                if protocol == Protocol.S7COMMPLUS:
                    raise RuntimeError(
                        f"S7CommPlus connection to {address}:{tcp_port} failed and protocol=S7COMMPLUS was explicitly requested"
                    )
                self._protocol = Protocol.LEGACY
                logger.info(f"S7CommPlus not available, using legacy S7 for {address}:{tcp_port}")
        else:
            self._protocol = Protocol.LEGACY

        # Always connect legacy client (needed for block ops, PLC control, etc.)
        self._legacy = LegacyClient()
        self._legacy.connect(address, rack, slot, tcp_port)
        logger.info(f"Legacy S7 connected to {address}:{tcp_port}")

        return self

    def _try_s7commplus(
        self,
        address: str,
        tcp_port: int,
        rack: int,
        slot: int,
        *,
        use_tls: bool = False,
        tls_cert: Optional[str] = None,
        tls_key: Optional[str] = None,
        tls_ca: Optional[str] = None,
        password: Optional[str] = None,
    ) -> bool:
        """Try to establish an S7CommPlus connection.

        Returns True if S7CommPlus data operations are available.
        """
        plus = S7CommPlusClient()
        try:
            plus.connect(
                host=address,
                port=tcp_port,
                rack=rack,
                slot=slot,
                use_tls=use_tls,
                tls_cert=tls_cert,
                tls_key=tls_key,
                tls_ca=tls_ca,
                password=password,
            )
        except Exception as e:
            logger.debug(f"S7CommPlus connection failed: {e}")
            return False

        if not plus.session_setup_ok:
            logger.debug("S7CommPlus session setup not OK, disconnecting")
            plus.disconnect()
            return False

        self._plus = plus
        return True

    def disconnect(self) -> int:
        """Disconnect from PLC.

        Returns:
            0 on success (matches snap7.Client).
        """
        if self._plus is not None:
            try:
                self._plus.disconnect()
            except Exception:
                pass
            self._plus = None

        if self._legacy is not None:
            try:
                self._legacy.disconnect()
            except Exception:
                pass
            self._legacy = None

        self._protocol = Protocol.AUTO
        return 0

    def db_read(self, db_number: int, start: int, size: int) -> bytearray:
        """Read raw bytes from a data block.

        Uses S7CommPlus when available, otherwise legacy S7.
        """
        if self._protocol == Protocol.S7COMMPLUS and self._plus is not None:
            return bytearray(self._plus.db_read(db_number, start, size))
        if self._legacy is not None:
            return self._legacy.db_read(db_number, start, size)
        raise RuntimeError("Not connected")

    def db_write(self, db_number: int, start: int, data: bytearray) -> int:
        """Write raw bytes to a data block.

        Uses S7CommPlus when available, otherwise legacy S7.

        Returns:
            0 on success (matches snap7.Client).
        """
        if self._protocol == Protocol.S7COMMPLUS and self._plus is not None:
            self._plus.db_write(db_number, start, bytes(data))
            return 0
        if self._legacy is not None:
            return self._legacy.db_write(db_number, start, data)
        raise RuntimeError("Not connected")

    def db_read_multi(self, items: list[tuple[int, int, int]]) -> list[bytearray]:
        """Read multiple data block regions in a single request.

        Uses S7CommPlus native multi-read when available.
        """
        if self._protocol == Protocol.S7COMMPLUS and self._plus is not None:
            return [bytearray(r) for r in self._plus.db_read_multi(items)]
        if self._legacy is not None:
            return [self._legacy.db_read(db, start, size) for db, start, size in items]
        raise RuntimeError("Not connected")

    def explore(self) -> bytes:
        """Browse the PLC object tree (S7CommPlus only).

        Raises:
            RuntimeError: If not connected via S7CommPlus.
        """
        if self._plus is None:
            raise RuntimeError("explore() requires S7CommPlus connection")
        return self._plus.explore()

    def __getattr__(self, name: str) -> Any:
        """Delegate unknown methods to the legacy client."""
        if name.startswith("_"):
            raise AttributeError(name)
        if self._legacy is not None:
            return getattr(self._legacy, name)
        raise AttributeError(f"'Client' object has no attribute {name!r} (not connected)")

    def __enter__(self) -> "Client":
        return self

    def __exit__(self, *args: Any) -> None:
        self.disconnect()

    def __repr__(self) -> str:
        if self.connected:
            return f"<s7.Client {self._host}:{self._port} protocol={self._protocol.value}>"
        return "<s7.Client disconnected>"
