"""Unified S7 client with protocol auto-discovery.

Provides a single client that automatically selects the best protocol
(S7CommPlus or legacy S7) for communicating with Siemens S7 PLCs.

Usage::

    from s7 import Client

    client = Client()
    client.connect("192.168.1.10", 0, 1)
    data = client.db_read(1, 0, 4)
    client.disconnect()
"""

import logging
from typing import Any, Optional

from snap7.client import Client as LegacyClient
from snap7.s7commplus.client import S7CommPlusClient

from ._protocol import Protocol

logger = logging.getLogger(__name__)


class Client:
    """Unified S7 client with protocol auto-discovery.

    Automatically selects the best protocol for the target PLC:

    - **S7CommPlus**: For S7-1200/1500 PLCs with full engineering access
    - **Legacy S7**: For S7-300/400 and S7-1200/1500 without S7CommPlus support

    When ``protocol=Protocol.AUTO`` (default), the client tries S7CommPlus
    first and falls back to legacy S7 transparently.

    Exposes the full legacy S7 client API. Methods not explicitly defined
    (block operations, PLC control, memory areas, etc.) are delegated to
    the underlying legacy client via ``__getattr__``.

    Examples::

        from s7 import Client

        # Auto-discover protocol
        client = Client()
        client.connect("192.168.1.10", 0, 1)
        data = client.db_read(1, 0, 4)
        print(client.protocol)  # Protocol.LEGACY or Protocol.S7COMMPLUS

        # Force legacy protocol
        client = Client()
        client.connect("192.168.1.10", 0, 1, protocol=Protocol.LEGACY)

        # S7CommPlus with TLS
        client = Client()
        client.connect("192.168.1.10", 0, 1, use_tls=True, password="secret")
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
            use_tls: Enable TLS for S7CommPlus V2+ connections.
            tls_cert: Path to client TLS certificate (PEM).
            tls_key: Path to client private key (PEM).
            tls_ca: Path to CA certificate for PLC verification (PEM).
            password: PLC password for S7CommPlus legitimation.

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
        """Attempt S7CommPlus connection and probe data operations.

        Returns True if S7CommPlus data operations are fully supported.
        On failure, cleans up the S7CommPlus connection.
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

        # The S7CommPlus client probes data ops internally and sets
        # using_legacy_fallback if they don't work. We don't want to use
        # its built-in fallback (that would create a duplicate legacy
        # connection), so we check and disconnect if it fell back.
        if plus.using_legacy_fallback:
            logger.debug("S7CommPlus connected but data ops not supported, disconnecting")
            try:
                plus.disconnect()
            except Exception:
                pass
            return False

        self._plus = plus
        return True

    def disconnect(self) -> int:
        """Disconnect from the PLC.

        Returns:
            0 on success.
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
        """Read data from a data block.

        Uses S7CommPlus when available, otherwise legacy S7.

        Args:
            db_number: DB number to read from.
            start: Start byte offset.
            size: Number of bytes to read.

        Returns:
            Data read from the DB.
        """
        if self._protocol == Protocol.S7COMMPLUS and self._plus is not None:
            return bytearray(self._plus.db_read(db_number, start, size))
        if self._legacy is not None:
            return self._legacy.db_read(db_number, start, size)
        raise RuntimeError("Not connected")

    def db_write(self, db_number: int, start: int, data: bytearray | bytes) -> int:
        """Write data to a data block.

        Uses S7CommPlus when available, otherwise legacy S7.

        Args:
            db_number: DB number to write to.
            start: Start byte offset.
            data: Data to write.

        Returns:
            0 on success.
        """
        if self._protocol == Protocol.S7COMMPLUS and self._plus is not None:
            self._plus.db_write(db_number, start, bytes(data))
            return 0
        if self._legacy is not None:
            return self._legacy.db_write(db_number, start, bytearray(data))
        raise RuntimeError("Not connected")

    def db_read_multi(self, items: list[tuple[int, int, int]]) -> list[bytearray]:
        """Read multiple data block regions.

        Uses S7CommPlus native multi-read when available, otherwise
        performs individual reads via legacy S7.

        Args:
            items: List of (db_number, start_offset, size) tuples.

        Returns:
            List of data for each item.
        """
        if self._protocol == Protocol.S7COMMPLUS and self._plus is not None:
            return [bytearray(r) for r in self._plus.db_read_multi(items)]
        if self._legacy is not None:
            return [self._legacy.db_read(db, start, size) for db, start, size in items]
        raise RuntimeError("Not connected")

    def explore(self) -> bytes:
        """Browse the PLC object tree (S7CommPlus only).

        Returns:
            Raw response payload.

        Raises:
            RuntimeError: If S7CommPlus is not active.
        """
        if self._plus is not None:
            return self._plus.explore()
        raise RuntimeError("explore() requires S7CommPlus protocol")

    def __getattr__(self, name: str) -> Any:
        """Delegate unknown attributes to the legacy client."""
        # Avoid infinite recursion for attributes accessed during __init__
        if name.startswith("_"):
            raise AttributeError(name)
        legacy = self.__dict__.get("_legacy")
        if legacy is not None:
            return getattr(legacy, name)
        raise AttributeError(f"'{type(self).__name__}' has no attribute '{name}'")

    def __enter__(self) -> "Client":
        return self

    def __exit__(self, *args: Any) -> None:
        self.disconnect()

    def __repr__(self) -> str:
        status = "connected" if self.connected else "disconnected"
        proto = self._protocol.value if self.connected else "none"
        return f"<s7.Client {self._host}:{self._port} {status} protocol={proto}>"
