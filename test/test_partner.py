import unittest as unittest
import snap7.partner

import logging
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
            (snap7.types.LocalPort, 0),
            (snap7.types.RemotePort, 102),
            (snap7.types.PingTimeout, 750),
            (snap7.types.SendTimeout, 10),
            (snap7.types.RecvTimeout, 3000),
            (snap7.types.SrcRef, 256),
            (snap7.types.DstRef, 0),
            (snap7.types.SrcTSap, 0),
            (snap7.types.PDURequest, 480),
            (snap7.types.WorkInterval, 100),
            (snap7.types.BSendTimeout, 3000),
            (snap7.types.BRecvTimeout, 3000),
            (snap7.types.RecoveryTime, 500L),
            (snap7.types.KeepAliveTime, 5000L),
        )
        for param, value in expected:
            self.assertEqual(self.partner.get_param(param), value)

        self.assertRaises(Exception, self.partner.get_param,
                          snap7.types.MaxClients)

    def test_get_stats(self):
        self.partner.get_stats()

    def test_get_status(self):
        self.partner.get_status()

    def test_get_times(self):
        self.partner.get_times()

    def test_set_param(self):
        values = (
            (snap7.types.PingTimeout, 800),
            (snap7.types.SendTimeout, 15),
            (snap7.types.RecvTimeout, 3500),
            (snap7.types.WorkInterval, 50),
            (snap7.types.SrcRef, 128),
            (snap7.types.DstRef, 128),
            (snap7.types.SrcTSap, 128),
            (snap7.types.PDURequest, 470),
            (snap7.types.BSendTimeout, 2000),
            (snap7.types.BRecvTimeout, 2000),
            (snap7.types.RecoveryTime, 400),
            (snap7.types.KeepAliveTime, 4000),
        )
        for param, value in values:
            self.partner.set_param(param, value)

        self.assertRaises(Exception, self.partner.set_param,
                          snap7.types.RemotePort, 1)

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
        self.partner.wait_as_b_send_completion()


if __name__ == '__main__':
    unittest.main()
