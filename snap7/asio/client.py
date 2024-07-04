from functools import partial
from snap7.client import Client
from asyncio import get_running_loop
from concurrent.futures import ThreadPoolExecutor


class AsyncClient:
    def __await__(self) -> "AsyncClient":
        return self

    def __init__(self) -> None:
        self.client = Client()
        self.loop = get_running_loop()
        self.pool = ThreadPoolExecutor()

    async def disconnect(self) -> None:
        await self.loop.run_in_executor(self.pool, lambda: self.client.disconnect)

    async def destroy(self) -> None:
        await self.loop.run_in_executor(self.pool, lambda: self.client.destroy)

    async def db_write(self, db_number: int, start: int, data: bytearray) -> int:
        # func: Callable[[], int] = lambda: self.client.db_write(db_number, start, data)
        func = partial(self.client.db_write, db_number, start, data)
        result: int = await self.loop.run_in_executor(self.pool, func)  # type: ignore
        return result

    async def db_get(self, db_number: int) -> bytearray:
        result: bytearray = await self.loop.run_in_executor(self.pool, lambda: self.client.db_get(db_number))
        return result
