"""Exercise the real SessionKey import path without optional cryptography."""

import subprocess
import sys
import textwrap


def test_missing_cryptography_aborts_connect_and_releases_socket() -> None:
    # A fresh interpreter avoids already-imported crypto modules masking a
    # missing dependency. Only the transport and PLC session data are mocked.
    script = textwrap.dedent("""
        import importlib.abc
        import sys
        from unittest.mock import MagicMock

        class NoCryptography(importlib.abc.MetaPathFinder):
            def find_spec(self, fullname, path=None, target=None):
                if fullname == "cryptography" or fullname.startswith("cryptography."):
                    raise ModuleNotFoundError("No module named 'cryptography'", name="cryptography")

        sys.meta_path.insert(0, NoCryptography())

        from snap7.error import S7ConnectionError
        from s7commplus.connection import S7CommPlusConnection
        from s7commplus.protocol import ProtocolVersion

        conn = S7CommPlusConnection("127.0.0.1")
        sockets = []

        def open_transport(timeout):
            sock = MagicMock()
            sockets.append(sock)
            conn._iso_conn.socket = sock
            conn._iso_conn.connected = True

        def create_session():
            conn._protocol_version = ProtocolVersion.V1
            conn._session_id = 7
            conn._server_session_version = b"version"
            conn._session_challenge = bytes(range(20))
            conn._public_key_fingerprint = "01:BD426B091F08731A"

        conn._iso_conn.connect = MagicMock(side_effect=open_transport)
        conn._init_ssl = MagicMock()
        conn._create_session = MagicMock(side_effect=create_session)
        conn._send_s7_data = MagicMock()

        for _ in range(2):
            try:
                conn.connect()
            except S7ConnectionError as exc:
                assert "python-snap7[s7commplus]" in str(exc)
                assert ".[s7commplus]" in str(exc)
                assert isinstance(exc.__cause__, ModuleNotFoundError)
            else:
                raise AssertionError("Missing cryptography did not abort connect")
            conn._send_s7_data.assert_not_called()
            assert not conn.connected
            assert not conn._session_ready
            assert not conn.session_setup_ok
            assert conn.session_id == 0
            assert conn._session_key is None
            assert conn._session_auth_public_key == b""
            assert conn._iso_conn.socket is None
            assert not conn._iso_conn.connected
            sockets[-1].close.assert_called_once()
            conn.disconnect()
            conn.disconnect()

        # TLS uses a different auth path and must not require legacy crypto.
        conn._tls_active = True
        conn._protocol_version = ProtocolVersion.V2
        conn._session_challenge = bytes(range(20))
        conn._public_key_fingerprint = "01:BD426B091F08731A"
        assert conn._try_session_key_auth() is None
    """)
    result = subprocess.run([sys.executable, "-c", script], capture_output=True, text=True, timeout=30)
    assert result.returncode == 0, result.stdout + result.stderr
