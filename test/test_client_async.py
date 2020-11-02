import asyncio
import ctypes
import logging
import pytest

logging.basicConfig(level=logging.WARNING)

pytestmark = pytest.mark.asyncio


async def test_wait_loop(testasyncclient):
    check_status = ctypes.c_int(-1)
    pending_checked = False
    # preparing Server values
    size = 40
    start = 0
    db = 1
    data = bytearray(40)
    testasyncclient.db_write(db_number=db, start=start, data=data)
    # Execute test
    p_data = testasyncclient.as_db_read(db, start, size)
    await asyncio.wait_for(testasyncclient.wait_loop(check_status), 10)
    data_result = bytearray(p_data)
    if not data == data_result:
        logging.warning("Test result is not as expected")
        raise ValueError
    if pending_checked is False:
        logging.warning("Pending was never reached, because Server was to fast,"
                        " but request to server was successfull.")
