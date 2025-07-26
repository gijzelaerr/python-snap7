import unittest
import pytest

from snap7.low_level.s7_server import S7Server
from snap7.low_level.s7_client import S7Client
from snap7.type import S7CpInfo, S7CpuInfo, S7OrderCode

@pytest.mark.s7
class TestS7(unittest.TestCase):

    def test_main(self):


        # con = snap7.Client()
        # con.connect("192.168.1.235", 0, 1, 102)
        # print(con.get_cpu_info())
        # con.destroy()

        s7 = S7Client()
        res = s7.connect_to("192.168.1.235", 0, 1, 102)
        if res != 0:
            print(f"Error  Connect {res}")
        else:
            print("Connected")

        # # #### Get CPU info
        # # #
        # cpu = S7CpuInfo()
        # res = s7.get_cpu_info(cpu)
        # if res != 0:
        #     print(f"Error getting CPU info {res}")
        #     exit(1)
        # print(cpu.ASName)
        # print(cpu.ModuleName)
        # print(cpu.Copyright)
        # print(cpu.SerialNumber)
        #
        # #### Get CP info
        # #
        # cp = S7CpInfo()
        # res = s7.get_cp_info(cp)
        # if res != 0:
        #     print(f"Error getting CP info {res}")
        #     exit(1)
        # print(cp)

        res = s7.get_exec_time()
        print(f"Execution time: {res} ms")

        order = S7OrderCode()
        res = s7.get_order_code(order)
        if res != 0:
            print(f"Error getting order code {res}")
        else:
            print(f"Order code: {order.OrderCode.decode('utf-8')}")
            print(f"Version: {order.V1}.{order.V2}.{order.V3}")

        assert res == 0

    def test_connect_and_disconnect(self):
        s7_server = S7Server()
        s7_client = S7Client()
        s7_server.start(ip="0.0.0.0", tcp_port=102)
        s7_client.connect(host="localhost", rack=0, slot=2, tcp_port=102)
        res_cli_disconnect = s7_client.disconnect()
        res_server_stop = s7_server.stop()
        assert res_cli_disconnect
        assert res_server_stop

    def test_setup_connection(self):
        s7_server = S7Server()
        s7_client = S7Client()
        s7_server.start(ip="0.0.0.0", tcp_port=102)
        s7_client.connect(host="localhost", rack=0, slot=2, tcp_port=102)
