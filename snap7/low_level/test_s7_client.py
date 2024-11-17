from .s7_client import S7Client


def test_connect():
    cli = S7Client()
    x = cli.connect_to("localhost", 0, 0, 1102)
    x
