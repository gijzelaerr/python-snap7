import asyncio
import ctypes
import time
import pytest
from multiprocessing import Process
from os import kill

import snap7
from snap7.server import mainloop
from snap7.exceptions import Snap7Exception


pytestmark = pytest.mark.asyncio

ip = "127.0.0.1"
tcpport = 1102
db_number = 1
rack = 1
slot = 1

pytest.valid_db_block = b'pp\x01\x01\x05\n\x00c\x00\x00\x00t\x00\x00\x00\x00\x01\x8d\xbe)2\xa1\x01' \
                        b'\x85V\x1f2\xa1\x00*\x00\x00\x00\x00\x00\x02\x01\x0f\x05c\x00#\x00\x00\x00' \
                        b'\x11\x04\x10\x01\x04\x01\x04\x01\x04\x01\x04\x01\x04\x01\x04\x01\x04\x01' \
                        b'\x04\x01\x04\x01\x04\x01\x04\x01\x04\x01\x04\x01\x04\x01\x04\x01\x04\x00' \
                        b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00' \
                        b'\x00\x00\x00\x00\x00\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'


@pytest.fixture
def server():
    process = Process(target=mainloop)
    process.start()
    time.sleep(2)  # wait for server to start
    yield process
    process.terminate()
    process.join(3)
    if process.is_alive():
        process.kill()


@pytest.fixture
def client():
    client_async = snap7.client_async.ClientAsync()
    client_async.connect(ip, rack, slot, tcpport)
    yield client_async
    client_async.disconnect()
    client_async.destroy()
    client_async.executor.shutdown()


@pytest.fixture
def event_loop():
    loop = asyncio.get_event_loop()
    yield loop
    loop.close()


async def test_as_compress(server, client, event_loop, monkeypatch):
    result = await client.as_compress(1000)
    assert result == 0


async def test_as_copy_ram_to_rom(server, client, event_loop):
    result = await client.as_copy_ram_to_rom(timeout=1)
    assert result == 0


async def test_as_ct_read(server, client, event_loop):
    data = b"\x10\x01"
    await client.as_ct_write(0, 1, data)
    result = await client.as_ct_read(0, 1)
    assert result == data


async def test_as_ct_write(server, client, event_loop):
    data = b"\x01\x11"
    result = await client.as_ct_write(0, 1, data)
    assert result == 0
    with pytest.raises(ValueError):
        await client.as_ct_write(0, 2, bytes(1))


async def test_as_db_fill(server, client, event_loop):
    filler = 31
    expected = bytearray(filler.to_bytes(1, byteorder="big") * 100)
    await client.as_db_fill(1, filler)
    result = await client.as_db_read(1, 0, 100)
    assert result == expected


async def test_as_eb_read(server, client, event_loop, monkeypatch):
    def mock_cli_ebread(pointer, start, size, data):
        return 0
    monkeypatch.setattr(client._library, 'Cli_EBRead', mock_cli_ebread)

    response = await client.as_eb_read(0, 1)
    assert isinstance(response, bytearray)
    assert len(response) == 1


async def test_as_eb_write(server, client, event_loop, monkeypatch):
    def mock_cli_ebwrite(pointer, start, size, data):
        return 0
    monkeypatch.setattr(client._library, 'Cli_EBWrite', mock_cli_ebwrite)
    response = await client.as_eb_write(0, 1, bytearray(1))
    assert isinstance(response, int)


async def test_as_full_upload(server, client, event_loop):
    with pytest.raises(Snap7Exception):
        await client.as_full_upload('DB', 1)


async def test_as_list_blocks_of_type(server, client, event_loop):
    await client.as_list_blocks_of_type("DB", 10)
    with pytest.raises(Exception):
        await client.as_list_blocks_of_type("NOblocktype", 10)


async def test_as_mb_read(server, client, event_loop, monkeypatch):
    def mock_cli_mbread(pointer, start, size, data):
        return 0
    monkeypatch.setattr(client._library, 'Cli_MBRead', mock_cli_mbread)
    response = await client.as_mb_read(0, 10)
    assert isinstance(response, bytearray)
    assert len(response) == 10


async def test_as_mb_write(server, client, event_loop, monkeypatch):
    def mock_cli_mbwrite(pointer, start, size, data):
        return 0
    monkeypatch.setattr(client._library, 'Cli_MBWrite', mock_cli_mbwrite)
    response = await client.as_mb_write(0, 1, bytearray(1))
    assert isinstance(response, int)


async def test_as_read_szl(server, client, event_loop):
    # partial list
    expected_number_of_records = 10
    expected_length_of_record = 34
    ssl_id = 0x001C
    response = await client.as_read_szl(ssl_id)
    assert expected_number_of_records == response.Header.NDR
    assert expected_length_of_record == response.Header.LengthDR
    # single data record
    expected = b"S C-C2UR28922012\x00\x00\x00\x00\x00\x00\x00\x00"
    ssl_id = 0x011C
    index = 0x0005
    response = await client.as_read_szl(ssl_id, index)
    result = bytes(response.Data)[2:26]
    assert result == expected
    # order number
    expected = b"6ES7 315-2EH14-0AB0 "
    ssl_id = 0x0111
    index = 0x0001
    response = await client.as_read_szl(ssl_id, index)
    result = bytes(response.Data[2:22])
    assert result == expected
    # invalid id
    ssl_id = 0xFFFF
    index = 0xFFFF
    with pytest.raises(Snap7Exception):
        await client.as_read_szl(ssl_id)
        await client.as_read_szl(ssl_id, index)


async def test_as_read_szl_list(server, client, event_loop):
    expected = b"\x00\x00\x00\x0f\x02\x00\x11\x00\x11\x01\x11\x0f\x12\x00\x12\x01"
    result = await client.as_read_szl_list()
    assert result[:16] == expected


async def test_as_tm_read(server, client, event_loop):
    data = b"\x10\x01"
    await client.as_tm_write(0, 1, data)
    result = await client.as_tm_read(0, 1)
    assert result == data


async def test_as_tm_write(server, client, event_loop):
    data = b"\x10\x01"
    assert 0 == await client.as_tm_write(0, 1, data)
    with pytest.raises(Snap7Exception):
        await client.as_tm_write(0, 100, bytes(200))
    with pytest.raises(ValueError):
        await client.as_tm_write(0, 2, bytes(2))


async def test_as_upload(server, client, event_loop):
    with pytest.raises(Snap7Exception):
        await client.upload(block_num=1)


async def test_as_db_read_write(server, client, event_loop):
    size = 40
    start = 0
    db = 1
    data = bytearray(40)
    await client.as_db_write(db_number=db, start=start, data=data)
    result = await client.as_db_read(db_number=db, start=start, size=size)
    assert result == data


async def test_as_download(server, client, event_loop):
    with pytest.raises(Snap7Exception):
        await client.as_download(block_num=1, data=pytest.valid_db_block)


async def test_as_ab_read(server, client, event_loop, monkeypatch):
    def mock_cli_abread(pointer, start, size, data):
        return 0
    monkeypatch.setattr(client._library, 'Cli_ABRead', mock_cli_abread)
    response = await client.as_ab_read(0, 10)
    assert isinstance(response, bytearray)
    assert len(response) == 10


async def test_as_ab_write(server, client, event_loop, monkeypatch):
    def mock_cli_abwrite(pointer, start, size, data):
        return 0
    monkeypatch.setattr(client._library, 'Cli_ABWrite', mock_cli_abwrite)
    response = await client.as_ab_write(0, bytearray(1))
    assert isinstance(response, int)


async def test_as_db_get(server, client, event_loop, monkeypatch):
    result = await client.as_db_get(db_number=1)
    assert len(result) == 65536
    assert isinstance(result, bytearray)


async def test_as_read_area(server, client, event_loop):
    amount = 1
    start = 1
    area = snap7.types.areas.DB
    dbnumber = 1
    data = bytearray(b"\x11")
    await client.as_write_area(area, dbnumber, start, data)
    result = await client.as_read_area(area, dbnumber, start, amount)
    assert result == data


async def test_as_write_area(server, client, event_loop):
    # Test write area with a DB
    area = snap7.types.areas.DB
    dbnumber = 1
    start = 1
    data = bytearray(b"\x11")
    await client.as_write_area(area, dbnumber, start, data)
    result = await client.as_read_area(area, dbnumber, start, 1)
    assert result == data
    # Test write area with a TM
    area = snap7.types.areas.TM
    dbnumber = 0
    timer = bytearray(b"\x12\x00")
    await client.as_write_area(area, dbnumber, start, timer)
    result = await client.as_read_area(area, dbnumber, start, 1)
    assert bytearray(result) == timer

    # Test write area with a CT
    area = snap7.types.areas.CT
    dbnumber = 0
    timer = bytearray(b"\x13\x00")
    await client.as_write_area(area, dbnumber, start, timer)
    result = await client.as_read_area(area, dbnumber, start, 1)
    assert bytearray(result) == timer
