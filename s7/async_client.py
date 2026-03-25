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
from snap7.s7commplus.async_client import S7CommPlusAsyncClient

from ._protocol import Protocol

logger = logging.getLogger(__name__)


class AsyncClient:
    """Unified async S7 client with protocol auto-discovery.

    Async counterpart of :class:`s7.Client`. Automatically selects the
    best protocol for the target PLC using asyncio for non-blocking I/O.

    Methods not explicitly defined are delegated to the underlying
    legacy async client via ``__getattr__``.

    Examples::

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
    ) -> "AsyncClient":
        """Connect to an S7 PLC.

        Args:
            address: PLC IP address or hostname.
            rack: PLC rack number.
            slot: PLC slot number.
            tcp_port: TCP port (default 102).
            protocol: Protocol selection. AUTO tries S7CommPlus first,
                then falls back to legacy S7.

        Returns:
            self, for method chaining.
        """
        self._host = address
        self._port = tcp_port
        self._rack = rack
        self._slot = slot

        if protocol in (Protocol.AUTO, Protocol.S7COMMPLUS):
            if await self._try_s7commplus(address, tcp_port, rack, slot):
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
    ) -> bool:
        """Attempt async S7CommPlus connection and probe data operations."""
        plus = S7CommPlusAsyncClient()
        try:
            await plus.connect(host=address, port=tcp_port, rack=rack, slot=slot)
        except Exception as e:
            logger.debug(f"Async S7CommPlus connection failed: {e}")
            return False

        if plus.using_legacy_fallback:
            logger.debug("S7CommPlus connected but data ops not supported, disconnecting")
            try:
                await plus.disconnect()
            except Exception:
                pass
            return False

        self._plus = plus
        return True

    async def disconnect(self) -> int:
        """Disconnect from the PLC.

        Returns:
            0 on success.
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
        """Read data from a data block.

        Args:
            db_number: DB number to read from.
            start: Start byte offset.
            size: Number of bytes to read.

        Returns:
            Data read from the DB.
        """
        if self._protocol == Protocol.S7COMMPLUS and self._plus is not None:
            return bytearray(await self._plus.db_read(db_number, start, size))
        if self._legacy is not None:
            return await self._legacy.db_read(db_number, start, size)
        raise RuntimeError("Not connected")

    async def db_write(self, db_number: int, start: int, data: bytearray | bytes) -> int:
        """Write data to a data block.

        Args:
            db_number: DB number to write to.
            start: Start byte offset.
            data: Data to write.

        Returns:
            0 on success.
        """
        if self._protocol == Protocol.S7COMMPLUS and self._plus is not None:
            await self._plus.db_write(db_number, start, bytes(data))
            return 0
        if self._legacy is not None:
            return await self._legacy.db_write(db_number, start, bytearray(data))
        raise RuntimeError("Not connected")

    async def db_read_multi(self, items: list[tuple[int, int, int]]) -> list[bytearray]:
        """Read multiple data block regions.

        Args:
            items: List of (db_number, start_offset, size) tuples.

        Returns:
            List of data for each item.
        """
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

        Returns:
            Raw response payload.
        """
        if self._plus is not None:
            return await self._plus.explore()
        raise RuntimeError("explore() requires S7CommPlus protocol")

    def __getattr__(self, name: str) -> Any:
        """Delegate unknown attributes to the legacy async client."""
        if name.startswith("_"):
            raise AttributeError(name)
        legacy = self.__dict__.get("_legacy")
        if legacy is not None:
            return getattr(legacy, name)
        raise AttributeError(f"'{type(self).__name__}' has no attribute '{name}'")

    async def __aenter__(self) -> "AsyncClient":
        return self

    async def __aexit__(self, *args: Any) -> None:
        await self.disconnect()

    def __repr__(self) -> str:
        status = "connected" if self.connected else "disconnected"
        proto = self._protocol.value if self.connected else "none"
        return f"<s7.AsyncClient {self._host}:{self._port} {status} protocol={proto}>"
