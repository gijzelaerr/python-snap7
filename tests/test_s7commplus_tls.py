"""Integration tests for S7CommPlus V2/V3 with TLS.

Tests the complete TLS connection flow including:
- V2 server + client with TLS and IntegrityId tracking
- V3 server + client with TLS
- Legitimation (password authentication) flow
- Async client with TLS
- Error handling for missing TLS

Requires the `cryptography` package for self-signed certificate generation.
"""

import struct
import tempfile
import time
from collections.abc import Generator
from pathlib import Path

import pytest

from snap7.s7commplus.server import S7CommPlusServer
from snap7.s7commplus.client import S7CommPlusClient
from snap7.s7commplus.protocol import ProtocolVersion

try:
    import ipaddress

    from cryptography import x509
    from cryptography.x509.oid import NameOID
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import rsa
    import datetime

    _has_cryptography = True
except ImportError:
    _has_cryptography = False

pytestmark = pytest.mark.skipif(not _has_cryptography, reason="requires cryptography package")

# Use high ports to avoid conflicts
V2_TEST_PORT = 11130
V3_TEST_PORT = 11131
V2_AUTH_PORT = 11132
V3_AUTH_PORT = 11133


@pytest.fixture(scope="module")
def tls_certs() -> Generator[dict[str, str], None, None]:
    """Generate self-signed TLS certificates for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
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
                x509.SubjectAlternativeName([
                    x509.DNSName("localhost"),
                    x509.IPAddress(ipaddress.IPv4Address("127.0.0.1")),
                ]),
                critical=False,
            )
            .sign(key, hashes.SHA256())
        )

        cert_path = str(Path(tmpdir) / "server.crt")
        key_path = str(Path(tmpdir) / "server.key")

        with open(cert_path, "wb") as f:
            f.write(cert.public_bytes(serialization.Encoding.PEM))

        with open(key_path, "wb") as f:
            f.write(
                key.private_bytes(
                    serialization.Encoding.PEM,
                    serialization.PrivateFormat.TraditionalOpenSSL,
                    serialization.NoEncryption(),
                )
            )

        yield {"cert": cert_path, "key": key_path}


def _make_server(
    protocol_version: int,
    password: str | None = None,
) -> S7CommPlusServer:
    """Create and configure an S7CommPlus server with test data blocks."""
    srv = S7CommPlusServer(protocol_version=protocol_version, password=password)

    srv.register_db(
        1,
        {
            "temperature": ("Real", 0),
            "pressure": ("Real", 4),
            "running": ("Bool", 8),
            "count": ("DInt", 10),
        },
    )
    srv.register_raw_db(2, bytearray(256))

    # Pre-populate DB1
    db1 = srv.get_db(1)
    assert db1 is not None
    struct.pack_into(">f", db1.data, 0, 23.5)
    struct.pack_into(">f", db1.data, 4, 1.013)
    db1.data[8] = 1
    struct.pack_into(">i", db1.data, 10, 42)

    return srv


@pytest.fixture()
def v2_server(tls_certs: dict[str, str]) -> Generator[S7CommPlusServer, None, None]:
    """V2 server with TLS."""
    srv = _make_server(ProtocolVersion.V2)
    srv.start(port=V2_TEST_PORT, use_tls=True, tls_cert=tls_certs["cert"], tls_key=tls_certs["key"])
    time.sleep(0.1)
    yield srv
    srv.stop()


@pytest.fixture()
def v3_server(tls_certs: dict[str, str]) -> Generator[S7CommPlusServer, None, None]:
    """V3 server with TLS."""
    srv = _make_server(ProtocolVersion.V3)
    srv.start(port=V3_TEST_PORT, use_tls=True, tls_cert=tls_certs["cert"], tls_key=tls_certs["key"])
    time.sleep(0.1)
    yield srv
    srv.stop()


@pytest.fixture()
def v2_auth_server(tls_certs: dict[str, str]) -> Generator[S7CommPlusServer, None, None]:
    """V2 server with TLS and password authentication."""
    srv = _make_server(ProtocolVersion.V2, password="secret123")
    srv.start(port=V2_AUTH_PORT, use_tls=True, tls_cert=tls_certs["cert"], tls_key=tls_certs["key"])
    time.sleep(0.1)
    yield srv
    srv.stop()


@pytest.fixture()
def v3_auth_server(tls_certs: dict[str, str]) -> Generator[S7CommPlusServer, None, None]:
    """V3 server with TLS and password authentication."""
    srv = _make_server(ProtocolVersion.V3, password="secret123")
    srv.start(port=V3_AUTH_PORT, use_tls=True, tls_cert=tls_certs["cert"], tls_key=tls_certs["key"])
    time.sleep(0.1)
    yield srv
    srv.stop()


class TestV2TLS:
    """Test V2 protocol with TLS."""

    def test_connect_disconnect(self, v2_server: S7CommPlusServer) -> None:
        client = S7CommPlusClient()
        client.connect("127.0.0.1", port=V2_TEST_PORT, use_tls=True)
        assert client.connected
        assert client.session_id != 0
        assert client.protocol_version == ProtocolVersion.V2
        client.disconnect()
        assert not client.connected

    def test_read_real(self, v2_server: S7CommPlusServer) -> None:
        client = S7CommPlusClient()
        client.connect("127.0.0.1", port=V2_TEST_PORT, use_tls=True)
        try:
            data = client.db_read(1, 0, 4)
            value = struct.unpack(">f", data)[0]
            assert abs(value - 23.5) < 0.001
        finally:
            client.disconnect()

    def test_write_and_read_back(self, v2_server: S7CommPlusServer) -> None:
        client = S7CommPlusClient()
        client.connect("127.0.0.1", port=V2_TEST_PORT, use_tls=True)
        try:
            client.db_write(1, 0, struct.pack(">f", 99.9))
            data = client.db_read(1, 0, 4)
            value = struct.unpack(">f", data)[0]
            assert abs(value - 99.9) < 0.1
        finally:
            client.disconnect()

    def test_multi_read(self, v2_server: S7CommPlusServer) -> None:
        client = S7CommPlusClient()
        client.connect("127.0.0.1", port=V2_TEST_PORT, use_tls=True)
        try:
            results = client.db_read_multi([
                (1, 0, 4),
                (1, 4, 4),
                (2, 0, 4),
            ])
            assert len(results) == 3
            temp = struct.unpack(">f", results[0])[0]
            assert abs(temp - 23.5) < 0.001
        finally:
            client.disconnect()

    def test_explore(self, v2_server: S7CommPlusServer) -> None:
        client = S7CommPlusClient()
        client.connect("127.0.0.1", port=V2_TEST_PORT, use_tls=True)
        try:
            response = client.explore()
            assert len(response) > 0
        finally:
            client.disconnect()


class TestV3TLS:
    """Test V3 protocol with TLS."""

    def test_connect_disconnect(self, v3_server: S7CommPlusServer) -> None:
        client = S7CommPlusClient()
        client.connect("127.0.0.1", port=V3_TEST_PORT, use_tls=True)
        assert client.connected
        assert client.session_id != 0
        assert client.protocol_version == ProtocolVersion.V3
        client.disconnect()
        assert not client.connected

    def test_read_real(self, v3_server: S7CommPlusServer) -> None:
        client = S7CommPlusClient()
        client.connect("127.0.0.1", port=V3_TEST_PORT, use_tls=True)
        try:
            data = client.db_read(1, 0, 4)
            value = struct.unpack(">f", data)[0]
            assert abs(value - 23.5) < 0.001
        finally:
            client.disconnect()

    def test_write_and_read_back(self, v3_server: S7CommPlusServer) -> None:
        client = S7CommPlusClient()
        client.connect("127.0.0.1", port=V3_TEST_PORT, use_tls=True)
        try:
            client.db_write(1, 0, struct.pack(">f", 88.8))
            data = client.db_read(1, 0, 4)
            value = struct.unpack(">f", data)[0]
            assert abs(value - 88.8) < 0.1
        finally:
            client.disconnect()

    def test_multi_read(self, v3_server: S7CommPlusServer) -> None:
        client = S7CommPlusClient()
        client.connect("127.0.0.1", port=V3_TEST_PORT, use_tls=True)
        try:
            results = client.db_read_multi([
                (1, 0, 4),
                (1, 10, 4),
            ])
            assert len(results) == 2
        finally:
            client.disconnect()

    def test_data_persists_across_clients(self, v3_server: S7CommPlusServer) -> None:
        c1 = S7CommPlusClient()
        c1.connect("127.0.0.1", port=V3_TEST_PORT, use_tls=True)
        c1.db_write(2, 0, b"\xca\xfe\xba\xbe")
        c1.disconnect()

        c2 = S7CommPlusClient()
        c2.connect("127.0.0.1", port=V3_TEST_PORT, use_tls=True)
        data = c2.db_read(2, 0, 4)
        c2.disconnect()

        assert data == b"\xca\xfe\xba\xbe"


class TestV2WithoutTLS:
    """Test that V2/V3 connections fail without TLS."""

    def test_v2_server_requires_tls_on_client(self, tls_certs: dict[str, str]) -> None:
        """V2 server reports V2 version; client should raise if no TLS."""
        # Start a V2 server WITHOUT TLS (so client can connect but gets V2 version)
        srv = _make_server(ProtocolVersion.V2)
        srv.start(port=V2_TEST_PORT + 10)
        time.sleep(0.1)
        try:
            client = S7CommPlusClient()
            with pytest.raises(Exception):
                # The server reports V2 but client didn't use TLS
                client.connect("127.0.0.1", port=V2_TEST_PORT + 10)
        finally:
            srv.stop()


class TestLegitimation:
    """Test password authentication (legitimation)."""

    def test_v2_connect_with_password(self, v2_auth_server: S7CommPlusServer) -> None:
        client = S7CommPlusClient()
        client.connect("127.0.0.1", port=V2_AUTH_PORT, use_tls=True, password="secret123")
        assert client.connected
        try:
            # Should be able to read after authentication
            data = client.db_read(1, 0, 4)
            value = struct.unpack(">f", data)[0]
            assert abs(value - 23.5) < 0.001
        finally:
            client.disconnect()

    def test_v3_connect_with_password(self, v3_auth_server: S7CommPlusServer) -> None:
        client = S7CommPlusClient()
        client.connect("127.0.0.1", port=V3_AUTH_PORT, use_tls=True, password="secret123")
        assert client.connected
        try:
            data = client.db_read(1, 0, 4)
            value = struct.unpack(">f", data)[0]
            assert abs(value - 23.5) < 0.001
        finally:
            client.disconnect()

    def test_v2_without_password_on_protected_server(self, v2_auth_server: S7CommPlusServer) -> None:
        """Connecting without password to a password-protected server should fail data ops."""
        client = S7CommPlusClient()
        client.connect("127.0.0.1", port=V2_AUTH_PORT, use_tls=True)
        try:
            # Server should reject data operations without authentication
            with pytest.raises(Exception):
                client.db_read(1, 0, 4)
        finally:
            client.disconnect()

    def test_v2_write_with_password(self, v2_auth_server: S7CommPlusServer) -> None:
        client = S7CommPlusClient()
        client.connect("127.0.0.1", port=V2_AUTH_PORT, use_tls=True, password="secret123")
        try:
            client.db_write(1, 0, struct.pack(">f", 55.5))
            data = client.db_read(1, 0, 4)
            value = struct.unpack(">f", data)[0]
            assert abs(value - 55.5) < 0.1
        finally:
            client.disconnect()


@pytest.mark.asyncio
class TestAsyncV2TLS:
    """Test async client with V2 TLS."""

    async def test_connect_disconnect(self, v2_server: S7CommPlusServer) -> None:
        from snap7.s7commplus.async_client import S7CommPlusAsyncClient

        client = S7CommPlusAsyncClient()
        await client.connect("127.0.0.1", port=V2_TEST_PORT, use_tls=True)
        assert client.connected
        assert client.session_id != 0
        assert client.protocol_version == ProtocolVersion.V2
        assert client.tls_active
        await client.disconnect()
        assert not client.connected

    async def test_read_real(self, v2_server: S7CommPlusServer) -> None:
        from snap7.s7commplus.async_client import S7CommPlusAsyncClient

        async with S7CommPlusAsyncClient() as client:
            await client.connect("127.0.0.1", port=V2_TEST_PORT, use_tls=True)
            data = await client.db_read(1, 0, 4)
            value = struct.unpack(">f", data)[0]
            assert abs(value - 23.5) < 0.001

    async def test_write_and_read_back(self, v2_server: S7CommPlusServer) -> None:
        from snap7.s7commplus.async_client import S7CommPlusAsyncClient

        async with S7CommPlusAsyncClient() as client:
            await client.connect("127.0.0.1", port=V2_TEST_PORT, use_tls=True)
            await client.db_write(1, 0, struct.pack(">f", 77.7))
            data = await client.db_read(1, 0, 4)
            value = struct.unpack(">f", data)[0]
            assert abs(value - 77.7) < 0.1


@pytest.mark.asyncio
class TestAsyncV3TLS:
    """Test async client with V3 TLS."""

    async def test_connect_disconnect(self, v3_server: S7CommPlusServer) -> None:
        from snap7.s7commplus.async_client import S7CommPlusAsyncClient

        client = S7CommPlusAsyncClient()
        await client.connect("127.0.0.1", port=V3_TEST_PORT, use_tls=True)
        assert client.connected
        assert client.protocol_version == ProtocolVersion.V3
        assert client.tls_active
        await client.disconnect()

    async def test_read_write(self, v3_server: S7CommPlusServer) -> None:
        from snap7.s7commplus.async_client import S7CommPlusAsyncClient

        async with S7CommPlusAsyncClient() as client:
            await client.connect("127.0.0.1", port=V3_TEST_PORT, use_tls=True)
            await client.db_write(2, 0, b"\xde\xad")
            data = await client.db_read(2, 0, 2)
            assert data == b"\xde\xad"


@pytest.mark.asyncio
class TestAsyncLegitimation:
    """Test async client with password authentication."""

    async def test_v2_connect_with_password(self, v2_auth_server: S7CommPlusServer) -> None:
        from snap7.s7commplus.async_client import S7CommPlusAsyncClient

        async with S7CommPlusAsyncClient() as client:
            await client.connect("127.0.0.1", port=V2_AUTH_PORT, use_tls=True, password="secret123")
            assert client.connected
            data = await client.db_read(1, 0, 4)
            value = struct.unpack(">f", data)[0]
            assert abs(value - 23.5) < 0.001
