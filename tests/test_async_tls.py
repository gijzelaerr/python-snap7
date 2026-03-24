"""Tests for S7CommPlus async client TLS support."""

import struct
import tempfile
import time
from collections.abc import Generator

import pytest

from snap7.error import S7ConnectionError
from snap7.s7commplus.async_client import S7CommPlusAsyncClient
from snap7.s7commplus.server import S7CommPlusServer
from snap7.s7commplus.protocol import ProtocolVersion

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
    subject = issuer = x509.Name([
        x509.NameAttribute(NameOID.COMMON_NAME, "localhost"),
    ])
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
    key_file.write(key.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.TraditionalOpenSSL,
        serialization.NoEncryption(),
    ))
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
