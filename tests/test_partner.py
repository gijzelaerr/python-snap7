import logging

import pytest
import unittest as unittest
from unittest import mock
from snap7.error import error_text

import snap7.partner
from snap7.type import Parameter

logging.basicConfig(level=logging.WARNING)


@pytest.mark.partner
class TestPartner(unittest.TestCase):
    def setUp(self) -> None:
        self.partner = snap7.partner.Partner()
        self.partner.start()

    def tearDown(self) -> None:
        self.partner.stop()
        self.partner.destroy()

    def test_as_b_send(self) -> None:
        self.partner.as_b_send()

    def test_b_send_recv(self) -> None:
        self.partner.b_send()
        # self.partner.b_recv()

    def test_check_as_b_recv_completion(self) -> None:
        self.partner.check_as_b_recv_completion()

    def test_check_as_b_send_completion(self) -> None:
        self.partner.check_as_b_send_completion()

    def test_create(self) -> None:
        self.partner.create()

    def test_destroy(self) -> None:
        self.partner.destroy()

    def test_error_text(self) -> None:
        error_text(0, context="partner")

    def test_get_last_error(self) -> None:
        self.partner.get_last_error()

    def test_get_param(self) -> None:
        expected = (
            (Parameter.LocalPort, 0),
            (Parameter.RemotePort, 102),
            (Parameter.PingTimeout, 750),
            (Parameter.SendTimeout, 10),
            (Parameter.RecvTimeout, 3000),
            (Parameter.SrcRef, 256),
            (Parameter.DstRef, 0),
            (Parameter.PDURequest, 480),
            (Parameter.WorkInterval, 100),
            (Parameter.BSendTimeout, 3000),
            (Parameter.BRecvTimeout, 3000),
            (Parameter.RecoveryTime, 500),
            (Parameter.KeepAliveTime, 5000),
        )
        for param, value in expected:
            self.assertEqual(self.partner.get_param(param), value)

        self.assertRaises(Exception, self.partner.get_param, Parameter.MaxClients)

    def test_get_stats(self) -> None:
        self.partner.get_stats()

    def test_get_status(self) -> None:
        self.partner.get_status()

    def test_get_times(self) -> None:
        self.partner.get_times()

    def test_set_param(self) -> None:
        values = (
            (Parameter.PingTimeout, 800),
            (Parameter.SendTimeout, 15),
            (Parameter.RecvTimeout, 3500),
            (Parameter.WorkInterval, 50),
            (Parameter.SrcRef, 128),
            (Parameter.DstRef, 128),
            (Parameter.SrcTSap, 128),
            (Parameter.PDURequest, 470),
            (Parameter.BSendTimeout, 2000),
            (Parameter.BRecvTimeout, 2000),
            (Parameter.RecoveryTime, 400),
            (Parameter.KeepAliveTime, 4000),
        )
        for param, value in values:
            self.partner.set_param(param, value)

        self.assertRaises(Exception, self.partner.set_param, Parameter.RemotePort, 1)

    def test_set_recv_callback(self) -> None:
        self.partner.set_recv_callback()

    def test_set_send_callback(self) -> None:
        self.partner.set_send_callback()

    def test_start(self) -> None:
        self.partner.start()

    def test_start_to(self) -> None:
        self.partner.start_to("0.0.0.0", "0.0.0.0", 0, 0)  # noqa: S104

    def test_stop(self) -> None:
        self.partner.stop()

    def test_wait_as_b_send_completion(self) -> None:
        self.assertRaises(RuntimeError, self.partner.wait_as_b_send_completion)


@pytest.mark.partner
class TestLibraryIntegration(unittest.TestCase):
    def setUp(self) -> None:
        # replace the function load_library with a mock
        self.loadlib_patch = mock.patch("snap7.partner.load_library")
        self.loadlib_func = self.loadlib_patch.start()

        # have load_library return another mock
        self.mocklib = mock.MagicMock()
        self.loadlib_func.return_value = self.mocklib

        # have the Par_Create of the mock return None
        self.mocklib.Par_Create.return_value = None

    def tearDown(self) -> None:
        # restore load_library
        self.loadlib_patch.stop()

    def test_create(self) -> None:
        snap7.partner.Partner()
        self.mocklib.Par_Create.assert_called_once()

    def test_gc(self) -> None:
        partner = snap7.partner.Partner()
        del partner
        self.mocklib.Par_Destroy.assert_called_once()


if __name__ == "__main__":
    unittest.main()
