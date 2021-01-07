"""
Snap7 async client used for connection to a siemens7 server.
"""
import asyncio
import logging
from ctypes import byref, Array

from snap7.common import check_error
from snap7.types import S7SZL
from .client import Client

from concurrent.futures import ThreadPoolExecutor
from functools import wraps, partial
from typing import Union, Tuple, Awaitable


class ClientAsync(Client):
    def __init__(self, max_workers=1):
        super().__init__()
        self.executor = ThreadPoolExecutor(max_workers=max_workers)

    def sync_to_async(self, func):
        @wraps(func)
        async def wrapper(*args, loop=None, executor=None, **kwargs):
            if loop is None:
                loop = asyncio.get_event_loop()
            pfunc = partial(func, *args, **kwargs)
            return await loop.run_in_executor(self.executor, pfunc)
        return wrapper

    async def as_compress(self, time) -> Awaitable[int]: # type: ignore
        func = self.sync_to_async(self.compress)
        return await func(time)

    async def as_copy_ram_to_rom(self, timeout=1) -> Awaitable[int]: # type: ignore
        func = self.sync_to_async(self.copy_ram_to_rom)
        return await func(timeout)

    async def as_ct_read(self, start: int, amount: int) -> Awaitable[bytearray]: # type: ignore
        func = self.sync_to_async(self.ct_read)
        return await func(start, amount)

    async def as_ct_write(self, start: int, amount: int, data: bytearray) -> Awaitable[int]: # type: ignore
        func = self.sync_to_async(self.ct_write)
        return await func(start, amount, data)

    async def as_db_fill(self, db_number: int, filler: int) -> Awaitable[int]: # type: ignore
        func = self.sync_to_async(self.db_fill)
        return await func(db_number, filler)

    async def as_eb_read(self, start: int, size: int) -> Awaitable[bytearray]: # type: ignore
        func = self.sync_to_async(self.eb_read)
        return await func(start, size)

    async def as_eb_write(self, start: int, size: int, data: bytearray) -> Awaitable[int]: # type: ignore
        func = self.sync_to_async(self.eb_write)
        return await func(start, size, data)

    async def as_full_upload(self, _type, block_num) -> Awaitable[bytearray, int]: # type: ignore
        func = self.sync_to_async(self.full_upload)
        return await func(_type, block_num)

    async def as_list_blocks_of_type(self, blocktype, size) -> Awaitable[Union[int, Array]]: # type: ignore
        func = self.sync_to_async(self.list_blocks_of_type)
        return await func(blocktype, size)

    async def as_mb_read(self, start: int, size: int) -> Awaitable[bytearray]: # type: ignore
        func = self.sync_to_async(self.mb_read)
        return await func(start, size)

    async def as_mb_write(self, start: int, size: int, data: bytearray) -> Awaitable[int]: # type: ignore
        func = self.sync_to_async(self.mb_write)
        return await func(start, size, data)

    async def as_read_szl(self, ssl_id: int, index: int = 0x0000) -> Awaitable[S7SZL]: # type: ignore
        func = self.sync_to_async(self.read_szl)
        return await func(ssl_id, index)

    async def as_read_szl_list(self) -> Awaitable[bytearray]: # type: ignore
        func = self.sync_to_async(self.read_szl_list)
        return await func()

    async def as_tm_read(self, start: int, amount: int) -> Awaitable[bytearray]: # type: ignore
        func = self.sync_to_async(self.tm_read)
        return await func(start, amount)

    async def as_tm_write(self, start: int, amount: int, data: bytearray) -> Awaitable[int]: # type: ignore
        func = self.sync_to_async(self.tm_write)
        return await func(start, amount, data)

    async def as_upload(self, block_num) -> Awaitable[bytearray]: # type: ignore
        func = self.sync_to_async(self.upload)
        return await func(block_num)

    async def as_db_read(self, db_number, start, size) -> Awaitable[bytearray]: # type: ignore
        func = self.sync_to_async(self.db_read)
        return await func(db_number, start, size)

    async def as_db_write(self, db_number, start, data) -> Awaitable[int]: # type: ignore
        func = self.sync_to_async(self.db_write)
        return await func(db_number, start, data)

    async def as_download(self, data, block_num=-1) -> Awaitable[int]: # type: ignore
        """
        Downloads a DB data into the AG asynchronously.
        A whole block (including header and footer) must be available into the
        user buffer.

        :param block_num: New Block number (or -1)
        :param data: the user buffer
        """
        func = self.sync_to_async(self.download)
        return await func(data, block_num)

    async def as_ab_read(self, start, size) -> Awaitable[bytearray]: # type: ignore
        func = self.sync_to_async(self.ab_read)
        return await func(start, size)

    async def as_ab_write(self, start, data) -> Awaitable[int]: # type: ignore
        func = self.sync_to_async(self.ab_write)
        return await func(start, data)

    async def as_db_get(self, db_number) -> Awaitable[bytearray]: # type: ignore
        func = self.sync_to_async(self.db_get)
        return await func(db_number)

    async def as_read_area(self, area, dbnumber, start, size) -> Awaitable[int]: # type: ignore
        func = self.sync_to_async(self.read_area)
        return await func(area, dbnumber, start, size)

    async def as_write_area(self, area, dbnumber, start, data) -> Awaitable[int]: # type: ignore
        func = self.sync_to_async(self.write_area)
        return await func(area, dbnumber, start, data)
