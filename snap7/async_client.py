"""
Async wrapper for the S7 client.

Provides an asyncio-compatible interface by running blocking S7 operations
in a thread pool executor via asyncio.to_thread().
"""

import asyncio
from datetime import datetime
from typing import Any, Callable, List, Optional, Tuple, Union

from ctypes import Array, c_int

from .client import Client
from .type import (
    Area,
    Block,
    BlocksList,
    CDataArrayType,
    Parameter,
    S7CpInfo,
    S7CpuInfo,
    S7DataItem,
    S7OrderCode,
    S7Protection,
    S7SZL,
    S7SZLList,
    TS7BlockInfo,
    WordLen,
)


class AsyncClient:
    """Async wrapper around the synchronous S7 Client.

    All blocking I/O operations are executed in a thread pool via
    asyncio.to_thread(), making them safe to use in async applications.

    Examples:
        >>> import asyncio
        >>> from snap7 import AsyncClient
        >>>
        >>> async def main():
        ...     client = AsyncClient()
        ...     await client.connect("192.168.1.10", 0, 1)
        ...     data = await client.db_read(1, 0, 4)
        ...     await client.disconnect()
        >>>
        >>> asyncio.run(main())
    """

    def __init__(self, lib_location: Optional[str] = None, **kwargs: Any):
        """Initialize async S7 client.

        Args:
            lib_location: Ignored. Kept for backwards compatibility.
        """
        self._client = Client(lib_location=lib_location, **kwargs)

    # --- Connection management ---

    async def connect(self, address: str, rack: int, slot: int, tcp_port: int = 102) -> "AsyncClient":
        """Connect to S7 PLC."""
        await asyncio.to_thread(self._client.connect, address, rack, slot, tcp_port)
        return self

    async def disconnect(self) -> int:
        """Disconnect from S7 device."""
        return await asyncio.to_thread(self._client.disconnect)

    def get_connected(self) -> bool:
        """Check if client is connected to PLC."""
        return self._client.get_connected()

    def create(self) -> None:
        """Create S7 client (no-op for native implementation)."""
        self._client.create()

    def destroy(self) -> None:
        """Destroy S7 client (no-op for native implementation)."""
        self._client.destroy()

    # --- DB operations ---

    async def db_read(self, db_number: int, start: int, size: int) -> bytearray:
        """Read data from DB."""
        return await asyncio.to_thread(self._client.db_read, db_number, start, size)

    async def db_write(self, db_number: int, start: int, data: bytearray) -> int:
        """Write data to DB."""
        return await asyncio.to_thread(self._client.db_write, db_number, start, data)

    async def db_get(self, db_number: int, size: int = 0) -> bytearray:
        """Get entire DB contents."""
        return await asyncio.to_thread(self._client.db_get, db_number, size)

    async def db_fill(self, db_number: int, filler: int, size: int = 0) -> int:
        """Fill DB with a filler byte."""
        return await asyncio.to_thread(self._client.db_fill, db_number, filler, size)

    # --- Area read/write ---

    async def read_area(self, area: Area, db_number: int, start: int, size: int) -> bytearray:
        """Read data from memory area."""
        return await asyncio.to_thread(self._client.read_area, area, db_number, start, size)

    async def write_area(self, area: Area, db_number: int, start: int, data: bytearray) -> int:
        """Write data to memory area."""
        return await asyncio.to_thread(self._client.write_area, area, db_number, start, data)

    async def read_multi_vars(self, items: Union[List[dict[str, Any]], "Array[S7DataItem]"]) -> Tuple[int, Any]:
        """Read multiple variables in a single request."""
        return await asyncio.to_thread(self._client.read_multi_vars, items)

    async def write_multi_vars(self, items: Union[List[dict[str, Any]], List[S7DataItem]]) -> int:
        """Write multiple variables in a single request."""
        return await asyncio.to_thread(self._client.write_multi_vars, items)

    # --- Convenience area methods ---

    async def ab_read(self, start: int, size: int) -> bytearray:
        """Read process outputs."""
        return await asyncio.to_thread(self._client.ab_read, start, size)

    async def ab_write(self, start: int, data: bytearray) -> int:
        """Write process outputs."""
        return await asyncio.to_thread(self._client.ab_write, start, data)

    async def eb_read(self, start: int, size: int) -> bytearray:
        """Read process inputs."""
        return await asyncio.to_thread(self._client.eb_read, start, size)

    async def eb_write(self, start: int, size: int, data: bytearray) -> int:
        """Write process inputs."""
        return await asyncio.to_thread(self._client.eb_write, start, size, data)

    async def mb_read(self, start: int, size: int) -> bytearray:
        """Read merkers (flags)."""
        return await asyncio.to_thread(self._client.mb_read, start, size)

    async def mb_write(self, start: int, size: int, data: bytearray) -> int:
        """Write merkers (flags)."""
        return await asyncio.to_thread(self._client.mb_write, start, size, data)

    async def tm_read(self, start: int, size: int) -> bytearray:
        """Read timers."""
        return await asyncio.to_thread(self._client.tm_read, start, size)

    async def tm_write(self, start: int, size: int, data: bytearray) -> int:
        """Write timers."""
        return await asyncio.to_thread(self._client.tm_write, start, size, data)

    async def ct_read(self, start: int, size: int) -> bytearray:
        """Read counters."""
        return await asyncio.to_thread(self._client.ct_read, start, size)

    async def ct_write(self, start: int, size: int, data: bytearray) -> int:
        """Write counters."""
        return await asyncio.to_thread(self._client.ct_write, start, size, data)

    # --- Block operations ---

    async def list_blocks(self) -> BlocksList:
        """List blocks in PLC."""
        return await asyncio.to_thread(self._client.list_blocks)

    async def list_blocks_of_type(self, block_type: Block, max_count: int) -> List[int]:
        """List blocks of a specific type."""
        return await asyncio.to_thread(self._client.list_blocks_of_type, block_type, max_count)

    async def get_block_info(self, block_type: Block, db_number: int) -> TS7BlockInfo:
        """Get information about a specific block."""
        return await asyncio.to_thread(self._client.get_block_info, block_type, db_number)

    def get_pg_block_info(self, data: bytearray) -> TS7BlockInfo:
        """Get block info from raw data (local operation, no I/O)."""
        return self._client.get_pg_block_info(data)

    async def upload(self, block_num: int) -> bytearray:
        """Upload a block from the PLC."""
        return await asyncio.to_thread(self._client.upload, block_num)

    async def download(self, data: bytearray, block_num: int = -1) -> int:
        """Download a block to the PLC."""
        return await asyncio.to_thread(self._client.download, data, block_num)

    async def delete(self, block_type: Block, block_num: int) -> int:
        """Delete a block from the PLC."""
        return await asyncio.to_thread(self._client.delete, block_type, block_num)

    async def full_upload(self, block_type: Block, block_num: int) -> Tuple[bytearray, int]:
        """Full upload of a block."""
        return await asyncio.to_thread(self._client.full_upload, block_type, block_num)

    # --- PLC control ---

    async def plc_stop(self) -> int:
        """Stop the PLC."""
        return await asyncio.to_thread(self._client.plc_stop)

    async def plc_hot_start(self) -> int:
        """Hot start the PLC."""
        return await asyncio.to_thread(self._client.plc_hot_start)

    async def plc_cold_start(self) -> int:
        """Cold start the PLC."""
        return await asyncio.to_thread(self._client.plc_cold_start)

    async def compress(self, timeout: int) -> int:
        """Compress PLC memory."""
        return await asyncio.to_thread(self._client.compress, timeout)

    async def copy_ram_to_rom(self, timeout: int = 0) -> int:
        """Copy RAM to ROM."""
        return await asyncio.to_thread(self._client.copy_ram_to_rom, timeout)

    # --- Info retrieval ---

    async def get_cpu_info(self) -> S7CpuInfo:
        """Get CPU information."""
        return await asyncio.to_thread(self._client.get_cpu_info)

    async def get_cpu_state(self) -> str:
        """Get CPU state."""
        return await asyncio.to_thread(self._client.get_cpu_state)

    async def get_cp_info(self) -> S7CpInfo:
        """Get CP info."""
        return await asyncio.to_thread(self._client.get_cp_info)

    async def get_order_code(self) -> S7OrderCode:
        """Get order code."""
        return await asyncio.to_thread(self._client.get_order_code)

    async def get_protection(self) -> S7Protection:
        """Get PLC protection info."""
        return await asyncio.to_thread(self._client.get_protection)

    # --- Date/time ---

    async def get_plc_datetime(self) -> datetime:
        """Get PLC date and time."""
        return await asyncio.to_thread(self._client.get_plc_datetime)

    async def set_plc_datetime(self, dt: datetime) -> int:
        """Set PLC date and time."""
        return await asyncio.to_thread(self._client.set_plc_datetime, dt)

    async def set_plc_system_datetime(self) -> int:
        """Set PLC date and time to system datetime."""
        return await asyncio.to_thread(self._client.set_plc_system_datetime)

    # --- SZL ---

    async def read_szl(self, ssl_id: int, index: int = 0) -> S7SZL:
        """Read System State List."""
        return await asyncio.to_thread(self._client.read_szl, ssl_id, index)

    async def read_szl_list(self) -> bytes:
        """Read SZL list."""
        return await asyncio.to_thread(self._client.read_szl_list)

    # --- ISO ---

    async def iso_exchange_buffer(self, data: bytearray) -> bytearray:
        """Exchange data over ISO connection."""
        return await asyncio.to_thread(self._client.iso_exchange_buffer, data)

    # --- Session / connection params (synchronous, no I/O) ---

    def set_connection_params(self, address: str, local_tsap: int, remote_tsap: int) -> None:
        """Set connection parameters."""
        self._client.set_connection_params(address, local_tsap, remote_tsap)

    def set_connection_type(self, connection_type: int) -> None:
        """Set connection type."""
        self._client.set_connection_type(connection_type)

    async def set_session_password(self, password: str) -> int:
        """Set session password."""
        return await asyncio.to_thread(self._client.set_session_password, password)

    async def clear_session_password(self) -> int:
        """Clear session password."""
        return await asyncio.to_thread(self._client.clear_session_password)

    def get_param(self, param: Parameter) -> int:
        """Get client parameter."""
        return self._client.get_param(param)

    def set_param(self, param: Parameter, value: int) -> int:
        """Set client parameter."""
        return self._client.set_param(param, value)

    # --- Status ---

    def get_exec_time(self) -> int:
        """Get last operation execution time in milliseconds."""
        return self._client.get_exec_time()

    def get_last_error(self) -> int:
        """Get last error code."""
        return self._client.get_last_error()

    def get_pdu_length(self) -> int:
        """Get negotiated PDU length."""
        return self._client.get_pdu_length()

    def error_text(self, error_code: int) -> str:
        """Get error text for an error code."""
        return self._client.error_text(error_code)

    # --- Context manager ---

    async def __aenter__(self) -> "AsyncClient":
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Async context manager exit."""
        await self.disconnect()
