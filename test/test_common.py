import logging
import unittest
import pathlib

from snap7.common import find_locally


logging.basicConfig(level=logging.WARNING)

file_name_test = "test.dll"


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
        file = find_locally(file_name_test.replace(".dll", ""))
        self.assertEqual(file, str(self.BASE_DIR / file_name_test))


if __name__ == '__main__':
    unittest.main()