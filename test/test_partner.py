import logging
import unittest as unittest
import snap7.partner
from snap7.snap7exceptions import Snap7Exception
import time


logging.basicConfig(level=logging.WARNING)

connectionStatusCodes = {
    0: {"func": "par_stopped", "desc": "Stopped."},
    1: {"func": "par_connecting", "desc": "Running, active and trying to connect."},
    2: {"func": "par_waiting", "desc": "Running, passive and waiting for a connection"},
    3: {"func": "par_connected", "desc": "Connected."},
    4: {"func": "par_sending", "desc": "Sending data."},
    5: {"func": "par_receiving", "desc": "Receiving data."},
    6: {"func": "par_binderror", "desc": "Error starting passive partner."},
}


class TestPartner(unittest.TestCase):
    
    def setUp(self):
        self.passive = snap7.partner.Partner(False)  # set as passive partner 
        self.passive.start_to("0.0.0.0", "127.0.0.1", 1002, 1000)
        self.partner = snap7.partner.Partner(True)  # set as active partner
        self.partner.start_to("0.0.0.0", "127.0.0.1", 1000, 1002)

        time.sleep(1)  # give some time to initiate connection.
        if self.passive.get_status().value != 3:
            logging.error("Passive Partner: %s" % connectionStatusCodes[self.passive.get_status().value]['desc'])
        if self.partner.get_status().value != 3:
            logging.error("Active Partner: %s" % connectionStatusCodes[self.partner.get_status().value]['desc'])

    def tearDown(self):
        self.partner.destroy()
        self.passive.destroy()

    def test_as_b_send_recv(self):
        test_string="test pass"
        self.partner.as_b_send(bytearray(test_string))
        self.partner.wait_as_b_send_completion(1)  # 1 second should be enough to pass message
        recv_msg = self.passive.b_recv()
        self.assertEqual(recv_msg, test_string, "Sent and Received message must match.")

    def test_b_send_recv(self):
        test_string="test pass"
        self.partner.b_send(bytearray(test_string))
        recv_msg = self.passive.b_recv()
        self.assertEqual(recv_msg, test_string, "Sent and Received message must match.")

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
            (snap7.snap7types.RemotePort, 102),
            (snap7.snap7types.PingTimeout, 750),
            (snap7.snap7types.SendTimeout, 10),
            (snap7.snap7types.RecvTimeout, 3000),
            (snap7.snap7types.SrcRef, 256),
            (snap7.snap7types.DstRef, 0),
            (snap7.snap7types.SrcTSap, 1000),
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


if __name__ == '__main__':
    unittest.main()
