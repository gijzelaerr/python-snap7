"""Tests for S7CommPlus async client TLS support."""

import contextlib
import ssl
import struct
import tempfile
import time
from collections.abc import Generator

import pytest

from snap7.error import S7ConnectionError
from s7commplus import connection
from s7commplus.async_client import S7CommPlusAsyncClient
from s7commplus.connection import S7CommPlusConnection
from s7commplus.server import S7CommPlusServer
from s7commplus.protocol import ProtocolVersion

TEST_PORT_V2 = 11130
TEST_PORT_V2_TLS = 11131


def _generate_self_signed_cert() -> tuple[str, str]:
    """Generate a self-signed certificate and key for testing.

    Returns:
        Tuple of (cert_path, key_path)
    """
    try:
        from cryptography import x509
        from cryptography.x509.oid import NameOID
        from cryptography.hazmat.primitives import hashes, serialization
        from cryptography.hazmat.primitives.asymmetric import rsa
        import datetime
    except ImportError:
        pytest.skip("cryptography package required for TLS tests")

    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    subject = issuer = x509.Name(
        [
            x509.NameAttribute(NameOID.COMMON_NAME, "localhost"),
        ]
    )
    cert = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(issuer)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(datetime.datetime.now(datetime.timezone.utc))
        .not_valid_after(datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=1))
        .add_extension(
            x509.SubjectAlternativeName([x509.IPAddress(ipaddress.IPv4Address("127.0.0.1"))]),
            critical=False,
        )
        .sign(key, hashes.SHA256())
    )

    cert_file = tempfile.NamedTemporaryFile(suffix=".pem", delete=False)
    cert_file.write(cert.public_bytes(serialization.Encoding.PEM))
    cert_file.close()

    key_file = tempfile.NamedTemporaryFile(suffix=".pem", delete=False)
    key_file.write(
        key.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.TraditionalOpenSSL,
            serialization.NoEncryption(),
        )
    )
    key_file.close()

    return cert_file.name, key_file.name


import ipaddress  # noqa: E402


class TestAsyncClientTLSPreconditions:
    """Test authenticate() and TLS precondition checks."""

    @pytest.mark.asyncio
    async def test_authenticate_not_connected(self) -> None:
        client = S7CommPlusAsyncClient()
        with pytest.raises(S7ConnectionError, match="Not connected"):
            await client.authenticate("password")

    @pytest.mark.asyncio
    async def test_authenticate_no_tls(self) -> None:
        client = S7CommPlusAsyncClient()
        client._connected = True
        client._tls_active = False
        client._oms_secret = None
        with pytest.raises(S7ConnectionError, match="requires TLS"):
            await client.authenticate("password")

    def test_tls_active_default_false(self) -> None:
        client = S7CommPlusAsyncClient()
        assert client.tls_active is False
        assert client.oms_secret is None

    @pytest.mark.asyncio
    async def test_disconnect_resets_tls_state(self) -> None:
        client = S7CommPlusAsyncClient()
        client._tls_active = True
        client._oms_secret = b"\x00" * 32
        await client.disconnect()
        assert client.tls_active is False
        assert client.oms_secret is None


class TestAsyncClientConnectTLSParams:
    """Test that connect() accepts TLS parameters."""

    @pytest.mark.asyncio
    async def test_connect_signature_accepts_tls_params(self) -> None:
        """Verify the connect method signature includes TLS params."""
        import inspect

        sig = inspect.signature(S7CommPlusAsyncClient.connect)
        params = list(sig.parameters.keys())
        assert "use_tls" in params
        assert "tls_cert" in params
        assert "tls_key" in params
        assert "tls_ca" in params


@pytest.fixture()
def v2_server() -> Generator[S7CommPlusServer, None, None]:
    """Start a V2 server without TLS for protocol negotiation tests."""
    srv = S7CommPlusServer(protocol_version=ProtocolVersion.V2)
    srv.register_raw_db(1, bytearray(256))
    db1 = srv.get_db(1)
    assert db1 is not None
    struct.pack_into(">f", db1.data, 0, 99.9)
    srv.start(port=TEST_PORT_V2)
    time.sleep(0.1)
    yield srv
    srv.stop()


class TestAsyncClientV2WithoutTLS:
    """Test that V2 connection without TLS raises appropriate error."""

    @pytest.mark.asyncio
    async def test_v2_without_tls_raises(self, v2_server: S7CommPlusServer) -> None:
        """V2 protocol requires TLS — connecting without should raise."""
        client = S7CommPlusAsyncClient()
        with pytest.raises(S7ConnectionError, match="V2.*requires TLS"):
            await client.connect("127.0.0.1", port=TEST_PORT_V2)


try:
    import cryptography  # noqa: F401

    _has_cryptography = True
except ImportError:
    _has_cryptography = False


@pytest.mark.skipif(not _has_cryptography, reason="requires cryptography package")
class TestAsyncClientV2WithTLS:
    """Test async client with V2 + TLS against emulated server."""

    @pytest.fixture()
    def tls_server(self) -> Generator[tuple[S7CommPlusServer, str, str], None, None]:
        """Start a V2 TLS server with self-signed cert."""
        cert_path, key_path = _generate_self_signed_cert()

        srv = S7CommPlusServer(protocol_version=ProtocolVersion.V2)
        srv.register_raw_db(1, bytearray(256))

        db1 = srv.get_db(1)
        assert db1 is not None
        struct.pack_into(">f", db1.data, 0, 42.0)

        srv.start(port=TEST_PORT_V2_TLS, use_tls=True, tls_cert=cert_path, tls_key=key_path)
        time.sleep(0.1)

        yield srv, cert_path, key_path

        srv.stop()

        import os

        os.unlink(cert_path)
        os.unlink(key_path)

    @pytest.mark.asyncio
    async def test_connect_with_tls(self, tls_server: tuple[S7CommPlusServer, str, str]) -> None:
        """Connect to V2 server with TLS enabled."""
        srv, cert_path, key_path = tls_server

        client = S7CommPlusAsyncClient()
        await client.connect("127.0.0.1", port=TEST_PORT_V2_TLS, use_tls=True, tls_ca=cert_path)

        try:
            assert client.connected
            assert client.tls_active
            assert client.protocol_version == ProtocolVersion.V2
        finally:
            await client.disconnect()

    @pytest.mark.asyncio
    async def test_integrity_id_tracking_enabled(self, tls_server: tuple[S7CommPlusServer, str, str]) -> None:
        """V2 connection should enable IntegrityId tracking."""
        srv, cert_path, key_path = tls_server

        client = S7CommPlusAsyncClient()
        await client.connect("127.0.0.1", port=TEST_PORT_V2_TLS, use_tls=True, tls_ca=cert_path)

        try:
            assert client._with_integrity_id is True
            # Counters may already be non-zero from the probe request
            assert client._integrity_id_read >= 0
            assert client._integrity_id_write >= 0
        finally:
            await client.disconnect()

    @pytest.mark.asyncio
    async def test_sequential_reads_and_writes_keep_integrity_counters_in_sync(
        self, tls_server: tuple[S7CommPlusServer, str, str]
    ) -> None:
        """Multiple V2 operations should succeed as both counters advance."""
        _, cert_path, _ = tls_server

        client = S7CommPlusAsyncClient()
        await client.connect("127.0.0.1", port=TEST_PORT_V2_TLS, use_tls=True, tls_ca=cert_path)

        try:
            initial_read_id = client._integrity_id_read
            initial_write_id = client._integrity_id_write

            for value in (b"first", b"second", b"third"):
                await client.db_write(1, 0, value)
                assert await client.db_read(1, 0, len(value)) == value

            assert client._integrity_id_read == initial_read_id + 3
            assert client._integrity_id_write == initial_write_id + 3
        finally:
            await client.disconnect()

    @pytest.mark.asyncio
    async def test_protocol_version_is_v2(self, tls_server: tuple[S7CommPlusServer, str, str]) -> None:
        """V2 server should report protocol version 2."""
        srv, cert_path, key_path = tls_server

        client = S7CommPlusAsyncClient()
        await client.connect("127.0.0.1", port=TEST_PORT_V2_TLS, use_tls=True, tls_ca=cert_path)

        try:
            assert client.protocol_version == ProtocolVersion.V2
        finally:
            await client.disconnect()

    @pytest.mark.asyncio
    async def test_context_manager_tls(self, tls_server: tuple[S7CommPlusServer, str, str]) -> None:
        """TLS connection via context manager."""
        srv, cert_path, key_path = tls_server

        async with S7CommPlusAsyncClient() as client:
            await client.connect("127.0.0.1", port=TEST_PORT_V2_TLS, use_tls=True, tls_ca=cert_path)
            assert client.connected
            assert client.tls_active

        assert not client.connected
        assert not client.tls_active


class TestSyncTLSBioPlumbing:
    """Unit tests for the sync client's MemoryBIO-based TLS-in-COTP routing.

    Exercises _do_tls_handshake / _send_s7_data / _recv_s7_data / _tls_flush_outgoing /
    _tls_read_incoming against a self-connected server SSLObject — no socket, no PLC.
    """

    def _make_connected_pair(self):
        import ssl
        from s7commplus.connection import S7CommPlusConnection

        cert_path, key_path = _generate_self_signed_cert()

        server_ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        server_ctx.load_cert_chain(cert_path, key_path)
        server_in, server_out = ssl.MemoryBIO(), ssl.MemoryBIO()
        server_ssl = server_ctx.wrap_bio(server_in, server_out, server_side=True)

        client_ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        client_ctx.check_hostname = False
        client_ctx.verify_mode = ssl.CERT_NONE

        conn = S7CommPlusConnection("127.0.0.1", 102)
        conn._incoming_bio = ssl.MemoryBIO()
        conn._outgoing_bio = ssl.MemoryBIO()
        conn._ssl_object = client_ctx.wrap_bio(conn._incoming_bio, conn._outgoing_bio)

        # Loopback iso layer: ciphertext the client "sends" goes into the server's
        # incoming BIO; bytes the client "receives" are popped from inbox.
        class _Loop:
            def __init__(self) -> None:
                self.inbox: list[bytes] = []

            def send_data(self, data: bytes) -> None:
                server_in.write(data)

            def receive_data(self) -> bytes:
                return self.inbox.pop(0)

        conn._iso_conn = _Loop()  # type: ignore[assignment]

        # Deterministic handshake pump (mirrors the BIO mechanism without blocking I/O).
        client_done = server_done = False
        for _ in range(40):
            try:
                conn._ssl_object.do_handshake()
                client_done = True
            except ssl.SSLWantReadError:
                pass
            out = conn._outgoing_bio.read()
            if out:
                server_in.write(out)
            try:
                server_ssl.do_handshake()
                server_done = True
            except ssl.SSLWantReadError:
                pass
            out = server_out.read()
            if out:
                conn._incoming_bio.write(out)
            if client_done and server_done:
                break
        assert client_done and server_done, "TLS handshake did not complete over MemoryBIO"

        conn._tls_active = True
        return conn, server_ssl, server_out

    def test_send_routes_encrypted_through_cotp_layer(self) -> None:
        conn, server_ssl, _server_out = self._make_connected_pair()
        frame = struct.pack(">BBH", 0x72, 0x02, 4) + b"\xde\xad\xbe\xef"
        conn._send_s7_data(frame)
        # The server decrypts exactly what the client sent through the BIO plumbing.
        assert server_ssl.read(65536) == frame

    def test_recv_routes_decrypted_from_cotp_layer(self) -> None:
        conn, server_ssl, server_out = self._make_connected_pair()
        payload = b"\x72\x02\x00\x00pushed-frame"
        server_ssl.write(payload)
        conn._iso_conn.inbox.append(server_out.read())  # queue ciphertext for the client
        assert conn._recv_s7_data() == payload


class TestTLSGroupSelection:
    """The ClientHello's supported_groups must offer X25519.

    Hardware evidence (CPU 1511F-1 PN, FW V2.9, plaintext port 102): a TIA
    Portal session against this CPU offers x25519 and is accepted; a
    ClientHello offering only secp256r1 is answered with a TCP RST during the
    TLS handshake. `set_ecdh_curve` cannot name X25519 on OpenSSL 3.0, so a
    fallback group there silently produced the rejected ClientHello.
    """

    X25519 = 0x001D
    SECP256R1 = 0x0017

    @staticmethod
    def _client_hello(ctx: ssl.SSLContext) -> bytes:
        """Drive a BIO handshake far enough to emit the ClientHello."""
        incoming, outgoing = ssl.MemoryBIO(), ssl.MemoryBIO()
        obj = ctx.wrap_bio(incoming, outgoing, server_side=False, server_hostname=None)
        with contextlib.suppress(ssl.SSLWantReadError):
            obj.do_handshake()
        return outgoing.read()

    @staticmethod
    def _supported_groups(record: bytes) -> list[int]:
        """Parse supported_groups (extension 10) out of a ClientHello record."""
        body = record[5:]  # past the TLS record header
        p = 6 + 32  # handshake header + legacy_version + random
        p += 1 + body[p]  # legacy_session_id
        p += 2 + int.from_bytes(body[p : p + 2], "big")  # cipher_suites
        p += 1 + body[p]  # compression_methods
        ext_end = p + 2 + int.from_bytes(body[p : p + 2], "big")
        p += 2
        while p + 4 <= ext_end:
            etype = int.from_bytes(body[p : p + 2], "big")
            elen = int.from_bytes(body[p + 2 : p + 4], "big")
            p += 4
            if etype == 10:
                n = int.from_bytes(body[p : p + 2], "big")
                return [int.from_bytes(body[p + 2 + i : p + 4 + i], "big") for i in range(0, n, 2)]
            p += elen
        return []

    def test_client_hello_offers_x25519(self) -> None:
        ctx = S7CommPlusConnection("127.0.0.1", 102)._setup_ssl_context()
        groups = self._supported_groups(self._client_hello(ctx))
        assert groups, "ClientHello carried no supported_groups extension"
        assert self.X25519 in groups, (
            f"ClientHello must offer x25519 - an S7-1500 RSTs without it; offered {[hex(g) for g in groups]}"
        )

    def test_no_fallback_group_when_x25519_unavailable(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """On OpenSSL builds that cannot name X25519, leave the groups alone.

        Narrowing to a different group is not graceful degradation: it
        restricts supported_groups to that group ALONE, which is exactly the
        ClientHello the PLC rejects. It also silently overrides the documented
        OPENSSL_CONF `Groups` workaround.
        """
        tried: list[str] = []

        def refuse(self: ssl.SSLContext, name: str) -> None:
            tried.append(name)
            raise ssl.SSLError("[EC: UNKNOWN_GROUP] unknown group")

        monkeypatch.setattr(ssl.SSLContext, "set_ecdh_curve", refuse)
        connection._set_s7_groups(ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT))

        assert tried == ["X25519"], f"must not narrow to a fallback group when X25519 is unavailable; tried {tried}"

    def test_client_hello_offers_x25519_even_when_curve_api_cannot_name_it(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """The regression, end to end: simulate OpenSSL 3.0 and read the wire.

        `test_client_hello_offers_x25519` above cannot catch this on a build
        where `set_ecdh_curve("X25519")` succeeds - the fallback never runs.
        Forcing the failure reproduces the hardware case: the ClientHello must
        still offer x25519, which holds only if the groups are left at the
        OpenSSL default instead of being narrowed to secp256r1.
        """
        real_set = ssl.SSLContext.set_ecdh_curve

        def refuse_x25519(self: ssl.SSLContext, name: str) -> None:
            if name == "X25519":
                raise ssl.SSLError("[EC: UNKNOWN_GROUP] unknown group")
            real_set(self, name)

        monkeypatch.setattr(ssl.SSLContext, "set_ecdh_curve", refuse_x25519)

        ctx = S7CommPlusConnection("127.0.0.1", 102)._setup_ssl_context()
        groups = self._supported_groups(self._client_hello(ctx))

        assert groups != [self.SECP256R1], (
            "supported_groups was narrowed to secp256r1 alone - this is the ClientHello an S7-1500 answers with a TCP RST"
        )
        assert self.X25519 in groups, f"ClientHello must still offer x25519; offered {[hex(g) for g in groups]}"
