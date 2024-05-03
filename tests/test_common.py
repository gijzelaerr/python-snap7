import logging
import pytest
import unittest
import pathlib

from snap7.common import _find_locally, load_library


logging.basicConfig(level=logging.WARNING)

file_name_test = "test.dll"


@pytest.mark.common
class TestCommon(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pass

    @classmethod
    def tearDownClass(cls):
        pass

    def setUp(self):
        self.BASE_DIR = pathlib.Path.cwd()
        self.file = self.BASE_DIR / file_name_test
        self.file.touch()

    def tearDown(self):
        self.file.unlink()

    def test_find_locally(self):
        file = _find_locally(file_name_test.replace(".dll", ""))
        self.assertEqual(file, str(self.BASE_DIR / file_name_test))

    def test_raise_error_if_no_library(self):
        with self.assertRaises(OSError):
            load_library("wronglocation")


if __name__ == "__main__":
    unittest.main()
