"""Destructors must tolerate module globals being cleared during shutdown."""

from __future__ import annotations

from unittest.mock import patch

from snap7.client import Client
from snap7.partner import Partner
from snap7.server import Server


def test_client_del_with_logger_cleared_does_not_raise() -> None:
    import snap7.client as client_mod

    c = Client()
    with patch.object(client_mod, "logger", None):
        c.__del__()  # noqa: PLC2801


def test_partner_del_with_logger_cleared_does_not_raise() -> None:
    import snap7.partner as partner_mod

    p = Partner()
    with patch.object(partner_mod, "logger", None):
        p.__del__()  # noqa: PLC2801


def test_server_del_with_logger_cleared_does_not_raise() -> None:
    import snap7.server as server_mod

    s = Server()
    with patch.object(server_mod, "logger", None):
        s.__del__()  # noqa: PLC2801
