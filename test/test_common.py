import ctypes
import gc
import logging
import struct
import time
import unittest
import platform
from datetime import datetime, timedelta, date
from multiprocessing import Process
from unittest import mock
import pathlib

from snap7.common import find_locally


logging.basicConfig(level=logging.WARNING)

ip = '127.0.0.1'
tcpport = 1102
db_number = 1
rack = 1
slot = 1

file_name_test = "test.dll"

class TestCommon(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        pass

    @classmethod
    def tearDownClass(cls):
        pass

    def setUp(self):
        self.BASE_DIR = pathlib.Path(__file__).resolve().parent.parent / "snap7"
        self.file = self.BASE_DIR / file_name_test
        self.file.touch()
    
    def tearDown(self):
        self.file.unlink()

    def test_find_locally(self):
        file = find_locally(file_name_test.replace(".dll", ""))
        self.assertEqual(file, str(self.BASE_DIR / file_name_test))

if __name__ == '__main__':
    unittest.main()
