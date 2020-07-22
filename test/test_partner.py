import logging
import unittest as unittest
import mock
import snap7.partner
from snap7.snap7exceptions import Snap7Exception


logging.basicConfig(level=logging.WARNING)


class TestPartner(unittest.TestCase):
    def setUp(self):
        self.partner = snap7.partner.Partner()
        self.partner.start()

    def test_as_b_send(self):
        self.partner.as_b_send()

    @unittest.skip("we don't recv something yet")
    def test_b_recv(self):
        self.partner.b_recv()

    def test_b_send(self):
        self.partner.b_send()

    def test_check_as_b_recv_completion(self):
        self.partner.check_as_b_recv_completion()

    def test_check_as_b_send_completion(self):
        self.partner.check_as_b_send_completion()

    def test_create(self):
        self.partner.create()

    def test_destroy(self):
        self.partner.destroy()

    def test_error_text(self):
        snap7.common.error_text(0, context="partner")

    def test_get_last_error(self):
        self.partner.get_last_error()

    def test_get_param(self):
        expected = (
            (snap7.snap7types.LocalPort, 0),
            (snap7.snap7types.RemotePort, 102),
            (snap7.snap7types.PingTimeout, 750),
            (snap7.snap7types.SendTimeout, 10),
            (snap7.snap7types.RecvTimeout, 3000),
            (snap7.snap7types.SrcRef, 256),
            (snap7.snap7types.DstRef, 0),
            (snap7.snap7types.SrcTSap, 0),
            (snap7.snap7types.PDURequest, 480),
            (snap7.snap7types.WorkInterval, 100),
            (snap7.snap7types.BSendTimeout, 3000),
            (snap7.snap7types.BRecvTimeout, 3000),
            (snap7.snap7types.RecoveryTime, 500),
            (snap7.snap7types.KeepAliveTime, 5000),
        )
        for param, value in expected:
            self.assertEqual(self.partner.get_param(param), value)

        self.assertRaises(Exception, self.partner.get_param,
                          snap7.snap7types.MaxClients)

    def test_get_stats(self):
        self.partner.get_stats()

    def test_get_status(self):
        self.partner.get_status()

    def test_get_times(self):
        self.partner.get_times()

    def test_set_param(self):
        values = (
            (snap7.snap7types.PingTimeout, 800),
            (snap7.snap7types.SendTimeout, 15),
            (snap7.snap7types.RecvTimeout, 3500),
            (snap7.snap7types.WorkInterval, 50),
            (snap7.snap7types.SrcRef, 128),
            (snap7.snap7types.DstRef, 128),
            (snap7.snap7types.SrcTSap, 128),
            (snap7.snap7types.PDURequest, 470),
            (snap7.snap7types.BSendTimeout, 2000),
            (snap7.snap7types.BRecvTimeout, 2000),
            (snap7.snap7types.RecoveryTime, 400),
            (snap7.snap7types.KeepAliveTime, 4000),
        )
        for param, value in values:
            self.partner.set_param(param, value)

        self.assertRaises(Exception, self.partner.set_param,
                          snap7.snap7types.RemotePort, 1)

    def test_set_recv_callback(self):
        self.partner.set_recv_callback()

    def test_set_send_callback(self):
        self.partner.set_send_callback()

    def test_start(self):
        self.partner.start()

    def test_start_to(self):
        self.partner.start_to('0.0.0.0', '0.0.0.0', 0, 0)

    def test_stop(self):
        self.partner.stop()

    def test_wait_as_b_send_completion(self):
        self.assertRaises(Snap7Exception, self.partner.wait_as_b_send_completion)


class TestLibraryIntegration(unittest.TestCase):
    def setUp(self):
        # replace the function load_library with a mock
        self.loadlib_patch = mock.patch('snap7.partner.load_library')
        self.loadlib_func = self.loadlib_patch.start()

        # have load_library return another mock
        self.mocklib = mock.MagicMock()
        self.loadlib_func.return_value = self.mocklib

        # have the Par_Create of the mock return None
        self.mocklib.Par_Create.return_value = None

    def tearDown(self):
        # restore load_library
        self.loadlib_patch.stop()

    def test_create(self):
        partner = snap7.partner.Partner()
        self.mocklib.Par_Create.assert_called_once()

    def test_gc(self):
        partner = snap7.partner.Partner()
        del partner
        self.mocklib.Par_Destroy.assert_called_once()


if __name__ == '__main__':
    unittest.main()
