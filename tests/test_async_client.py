from snap7.asio.client import AsyncClient
from snap7.server import mainloop
from unittest import IsolatedAsyncioTestCase, main
from multiprocessing import Process
from time import sleep


class AsyncClientTest(IsolatedAsyncioTestCase):
    process = None

    @classmethod
    def setUpClass(cls) -> None:
        cls.process = Process(target=mainloop)
        cls.process.start()
        sleep(2)  # wait for server to start

    @classmethod
    def tearDownClass(cls) -> None:
        if cls.process:
            cls.process.terminate()
            cls.process.join(1)
            if cls.process.is_alive():
                cls.process.kill()

    async def asyncSetUp(self) -> None:
        self.client = AsyncClient()

    async def asyncTearDown(self) -> None:
        await self.client.disconnect()
        await self.client.destroy()

    async def test_db_write(self) -> None:
        size = 40
        data = bytearray(size)
        await self.client.db_write(db_number=1, start=0, data=data)

    async def test_db_get(self) -> None:
        await self.client.db_get(db_number=1)


if __name__ == "__main__":
    main()
