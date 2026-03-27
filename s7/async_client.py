"""Unified async S7 client with protocol auto-discovery.

Provides a single async client that automatically selects the best protocol
(S7CommPlus or legacy S7) for communicating with Siemens S7 PLCs.

Usage::

    from s7 import AsyncClient

    async with AsyncClient() as client:
        await client.connect("192.168.1.10", 0, 1)
        data = await client.db_read(1, 0, 4)
"""

import logging
from typing import Any, Optional

from snap7.async_client import AsyncClient as LegacyAsyncClient

from ._protocol import Protocol
from ._s7commplus_async_client import S7CommPlusAsyncClient

logger = logging.getLogger(__name__)


class AsyncClient:
    """Unified async S7 client with protocol auto-discovery.

    Async counterpart of :class:`s7.Client`. Automatically selects the
    best protocol for the target PLC using asyncio for non-blocking I/O.

    Methods not explicitly defined are delegated to the underlying
    legacy async client via ``__getattr__``.

    Example::

        from s7 import AsyncClient

        async with AsyncClient() as client:
            await client.connect("192.168.1.10", 0, 1)
            data = await client.db_read(1, 0, 4)
            print(client.protocol)
    """

    def __init__(self) -> None:
        self._legacy: Optional[LegacyAsyncClient] = None
        self._plus: Optional[S7CommPlusAsyncClient] = None
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

    async def connect(
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
    ) -> "AsyncClient":
        """Connect to an S7 PLC.

        Args:
            address: PLC IP address or hostname.
            rack: PLC rack number.
            slot: PLC slot number.
            tcp_port: TCP port (default 102).
            protocol: Protocol selection. AUTO tries S7CommPlus first,
                then falls back to legacy S7.
            use_tls: Whether to activate TLS after InitSSL.
            tls_cert: Path to client TLS certificate (PEM).
            tls_key: Path to client private key (PEM).
            tls_ca: Path to CA certificate for PLC verification (PEM).

        Returns:
            self, for method chaining.
        """
        self._host = address
        self._port = tcp_port
        self._rack = rack
        self._slot = slot

        if protocol in (Protocol.AUTO, Protocol.S7COMMPLUS):
            if await self._try_s7commplus(
                address,
                tcp_port,
                rack,
                slot,
                use_tls=use_tls,
                tls_cert=tls_cert,
                tls_key=tls_key,
                tls_ca=tls_ca,
            ):
                self._protocol = Protocol.S7COMMPLUS
                logger.info(f"Async connected to {address}:{tcp_port} using S7CommPlus")
            else:
                if protocol == Protocol.S7COMMPLUS:
                    raise RuntimeError(
                        f"S7CommPlus connection to {address}:{tcp_port} failed and protocol=S7COMMPLUS was explicitly requested"
                    )
                self._protocol = Protocol.LEGACY
                logger.info(f"S7CommPlus not available, using legacy S7 for {address}:{tcp_port}")
        else:
            self._protocol = Protocol.LEGACY

        # Always connect legacy client
        self._legacy = LegacyAsyncClient()
        await self._legacy.connect(address, rack, slot, tcp_port)
        logger.info(f"Async legacy S7 connected to {address}:{tcp_port}")

        return self

    async def _try_s7commplus(
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
    ) -> bool:
        """Try to establish an S7CommPlus connection."""
        plus = S7CommPlusAsyncClient()
        try:
            await plus.connect(
                host=address,
                port=tcp_port,
                rack=rack,
                slot=slot,
                use_tls=use_tls,
                tls_cert=tls_cert,
                tls_key=tls_key,
                tls_ca=tls_ca,
            )
        except Exception as e:
            logger.debug(f"S7CommPlus connection failed: {e}")
            return False

        if not plus.session_setup_ok:
            logger.debug("S7CommPlus session setup not OK, disconnecting")
            await plus.disconnect()
            return False

        self._plus = plus
        return True

    async def disconnect(self) -> int:
        """Disconnect from PLC.

        Returns:
            0 on success (matches snap7.AsyncClient).
        """
        if self._plus is not None:
            try:
                await self._plus.disconnect()
            except Exception:
                pass
            self._plus = None

        if self._legacy is not None:
            try:
                await self._legacy.disconnect()
            except Exception:
                pass
            self._legacy = None

        self._protocol = Protocol.AUTO
        return 0

    async def db_read(self, db_number: int, start: int, size: int) -> bytearray:
        """Read raw bytes from a data block."""
        if self._protocol == Protocol.S7COMMPLUS and self._plus is not None:
            return bytearray(await self._plus.db_read(db_number, start, size))
        if self._legacy is not None:
            return await self._legacy.db_read(db_number, start, size)
        raise RuntimeError("Not connected")

    async def db_write(self, db_number: int, start: int, data: bytearray) -> int:
        """Write raw bytes to a data block.

        Returns:
            0 on success (matches snap7.AsyncClient).
        """
        if self._protocol == Protocol.S7COMMPLUS and self._plus is not None:
            await self._plus.db_write(db_number, start, bytes(data))
            return 0
        if self._legacy is not None:
            return await self._legacy.db_write(db_number, start, data)
        raise RuntimeError("Not connected")

    async def db_read_multi(self, items: list[tuple[int, int, int]]) -> list[bytearray]:
        """Read multiple data block regions in a single request."""
        if self._protocol == Protocol.S7COMMPLUS and self._plus is not None:
            return [bytearray(r) for r in await self._plus.db_read_multi(items)]
        if self._legacy is not None:
            results = []
            for db, start, size in items:
                results.append(await self._legacy.db_read(db, start, size))
            return results
        raise RuntimeError("Not connected")

    async def explore(self) -> bytes:
        """Browse the PLC object tree (S7CommPlus only).

        Raises:
            RuntimeError: If not connected via S7CommPlus.
        """
        if self._plus is None:
            raise RuntimeError("explore() requires S7CommPlus connection")
        return await self._plus.explore()

    def __getattr__(self, name: str) -> Any:
        """Delegate unknown methods to the legacy client."""
        if name.startswith("_"):
            raise AttributeError(name)
        if self._legacy is not None:
            return getattr(self._legacy, name)
        raise AttributeError(f"'AsyncClient' object has no attribute {name!r} (not connected)")

    async def __aenter__(self) -> "AsyncClient":
        return self

    async def __aexit__(self, *args: Any) -> None:
        await self.disconnect()

    def __repr__(self) -> str:
        if self.connected:
            return f"<s7.AsyncClient {self._host}:{self._port} protocol={self._protocol.value}>"
        return "<s7.AsyncClient disconnected>"
