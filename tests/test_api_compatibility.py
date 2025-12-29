"""
API Compatibility Tests.

Verify that the native Python implementation maintains API compatibility
with the master branch (clib-based) python-snap7.
"""

import inspect
import time
from ctypes import c_char
from typing import Generator, Tuple

import pytest

import snap7
from snap7 import Client, Server, Partner, Logo
from snap7 import Area, Block, WordLen, SrvEvent, SrvArea


class TestPublicExports:
    """Verify __init__.py exports match expected public API."""

    def test_client_exported(self) -> None:
        """Client class is exported from snap7."""
        assert hasattr(snap7, "Client")
        assert snap7.Client is Client

    def test_server_exported(self) -> None:
        """Server class is exported from snap7."""
        assert hasattr(snap7, "Server")
        assert snap7.Server is Server

    def test_partner_exported(self) -> None:
        """Partner class is exported from snap7."""
        assert hasattr(snap7, "Partner")
        assert snap7.Partner is Partner

    def test_logo_exported(self) -> None:
        """Logo class is exported from snap7."""
        assert hasattr(snap7, "Logo")
        assert snap7.Logo is Logo

    def test_area_enum_exported(self) -> None:
        """Area enum is exported from snap7."""
        assert hasattr(snap7, "Area")
        assert snap7.Area is Area

    def test_block_enum_exported(self) -> None:
        """Block enum is exported from snap7."""
        assert hasattr(snap7, "Block")
        assert snap7.Block is Block

    def test_wordlen_enum_exported(self) -> None:
        """WordLen enum is exported from snap7."""
        assert hasattr(snap7, "WordLen")
        assert snap7.WordLen is WordLen

    def test_srvevent_exported(self) -> None:
        """SrvEvent is exported from snap7."""
        assert hasattr(snap7, "SrvEvent")
        assert snap7.SrvEvent is SrvEvent

    def test_srvarea_exported(self) -> None:
        """SrvArea enum is exported from snap7."""
        assert hasattr(snap7, "SrvArea")
        assert snap7.SrvArea is SrvArea

    def test_row_exported(self) -> None:
        """Row class is exported from snap7."""
        assert hasattr(snap7, "Row")

    def test_db_exported(self) -> None:
        """DB class is exported from snap7."""
        assert hasattr(snap7, "DB")


class TestClientAPI:
    """Verify Client class has all expected methods from master branch."""

    # Complete list of expected Client methods from master branch
    EXPECTED_CLIENT_METHODS = [
        # Lifecycle
        "create",
        "destroy",
        # Connection
        "connect",
        "disconnect",
        "get_connected",
        "set_connection_params",
        "set_connection_type",
        # Basic read/write
        "db_read",
        "db_write",
        "db_get",
        "db_fill",
        "read_area",
        "write_area",
        "read_multi_vars",
        "write_multi_vars",
        # Memory area convenience methods
        "ab_read",
        "ab_write",
        "eb_read",
        "eb_write",
        "mb_read",
        "mb_write",
        "tm_read",
        "tm_write",
        "ct_read",
        "ct_write",
        # Block operations
        "list_blocks",
        "list_blocks_of_type",
        "get_block_info",
        "get_pg_block_info",
        "upload",
        "download",
        "delete",
        "full_upload",
        # PLC control
        "plc_stop",
        "plc_hot_start",
        "plc_cold_start",
        "get_cpu_state",
        "get_cpu_info",
        # System info
        "get_pdu_length",
        "get_plc_datetime",
        "set_plc_datetime",
        "set_plc_system_datetime",
        "get_order_code",
        "get_cp_info",
        "get_protection",
        "get_exec_time",
        "get_last_error",
        "read_szl",
        "read_szl_list",
        # Misc
        "compress",
        "copy_ram_to_rom",
        "iso_exchange_buffer",
        "error_text",
        # Session
        "set_session_password",
        "clear_session_password",
        # Parameters
        "get_param",
        "set_param",
        # Async methods
        "as_ab_read",
        "as_ab_write",
        "as_db_read",
        "as_db_write",
        "as_db_fill",
        "as_db_get",
        "as_eb_read",
        "as_eb_write",
        "as_mb_read",
        "as_mb_write",
        "as_tm_read",
        "as_tm_write",
        "as_ct_read",
        "as_ct_write",
        "as_read_area",
        "as_write_area",
        "as_download",
        "as_upload",
        "as_full_upload",
        "as_list_blocks_of_type",
        "as_read_szl",
        "as_read_szl_list",
        "as_compress",
        "as_copy_ram_to_rom",
        "wait_as_completion",
        "check_as_completion",
        "set_as_callback",
    ]

    @pytest.mark.parametrize("method_name", EXPECTED_CLIENT_METHODS)
    def test_client_has_method(self, method_name: str) -> None:
        """Client class has expected method."""
        assert hasattr(Client, method_name), f"Client missing method: {method_name}"
        assert callable(getattr(Client, method_name)), f"Client.{method_name} is not callable"


class TestServerAPI:
    """Verify Server class has all expected methods from master branch."""

    EXPECTED_SERVER_METHODS = [
        "create",
        "destroy",
        "start",
        "stop",
        "start_to",
        "register_area",
        "unregister_area",
        "lock_area",
        "unlock_area",
        "get_status",
        "set_events_callback",
        "set_read_events_callback",
        "event_text",
        "pick_event",
        "clear_events",
        "get_mask",
        "set_mask",
        "get_param",
        "set_param",
        "set_cpu_status",
    ]

    @pytest.mark.parametrize("method_name", EXPECTED_SERVER_METHODS)
    def test_server_has_method(self, method_name: str) -> None:
        """Server class has expected method."""
        assert hasattr(Server, method_name), f"Server missing method: {method_name}"
        assert callable(getattr(Server, method_name)), f"Server.{method_name} is not callable"


class TestPartnerAPI:
    """Verify Partner class has all expected methods from master branch."""

    EXPECTED_PARTNER_METHODS = [
        "create",
        "destroy",
        "start",
        "stop",
        "start_to",
        "b_send",
        "b_recv",
        "as_b_send",
        "check_as_b_send_completion",
        "wait_as_b_send_completion",
        "check_as_b_recv_completion",
        "get_status",
        "get_stats",
        "get_times",
        "get_last_error",
        "get_param",
        "set_param",
    ]

    @pytest.mark.parametrize("method_name", EXPECTED_PARTNER_METHODS)
    def test_partner_has_method(self, method_name: str) -> None:
        """Partner class has expected method."""
        assert hasattr(Partner, method_name), f"Partner missing method: {method_name}"
        assert callable(getattr(Partner, method_name)), f"Partner.{method_name} is not callable"


class TestLogoAPI:
    """Verify Logo class has all expected methods."""

    EXPECTED_LOGO_METHODS = [
        "connect",
        "disconnect",
        "read",
        "write",
    ]

    @pytest.mark.parametrize("method_name", EXPECTED_LOGO_METHODS)
    def test_logo_has_method(self, method_name: str) -> None:
        """Logo class has expected method."""
        assert hasattr(Logo, method_name), f"Logo missing method: {method_name}"
        assert callable(getattr(Logo, method_name)), f"Logo.{method_name} is not callable"


class TestClientMethodSignatures:
    """Verify Client method signatures match expected patterns."""

    def test_connect_signature(self) -> None:
        """connect() has correct signature."""
        sig = inspect.signature(Client.connect)
        params = list(sig.parameters.keys())
        assert "address" in params
        assert "rack" in params
        assert "slot" in params
        assert "tcp_port" in params

    def test_db_read_signature(self) -> None:
        """db_read() has correct signature."""
        sig = inspect.signature(Client.db_read)
        params = list(sig.parameters.keys())
        assert "db_number" in params
        assert "start" in params
        assert "size" in params

    def test_db_write_signature(self) -> None:
        """db_write() has correct signature."""
        sig = inspect.signature(Client.db_write)
        params = list(sig.parameters.keys())
        assert "db_number" in params
        assert "start" in params
        assert "data" in params

    def test_read_area_signature(self) -> None:
        """read_area() has correct signature."""
        sig = inspect.signature(Client.read_area)
        params = list(sig.parameters.keys())
        assert "area" in params
        assert "db_number" in params
        assert "start" in params
        assert "size" in params

    def test_delete_signature(self) -> None:
        """delete() has correct signature."""
        sig = inspect.signature(Client.delete)
        params = list(sig.parameters.keys())
        assert "block_type" in params
        assert "block_num" in params

    def test_full_upload_signature(self) -> None:
        """full_upload() has correct signature."""
        sig = inspect.signature(Client.full_upload)
        params = list(sig.parameters.keys())
        assert "block_type" in params
        assert "block_num" in params


@pytest.fixture
def server_client_pair() -> Generator[Tuple[Server, Client], None, None]:
    """Fixture that provides a connected server and client for behavioral tests."""
    server = Server()
    port = 11102

    # Create and register test memory areas
    size = 100
    db_data = bytearray(size)
    db_data[0] = 0x42
    db_data[1] = 0xFF

    db_array = (c_char * size).from_buffer(db_data)
    server.register_area(SrvArea.DB, 1, db_array)

    server.start(port)
    time.sleep(0.2)

    client = Client()
    try:
        client.connect("127.0.0.1", 0, 1, port)
        yield server, client
    finally:
        try:
            client.disconnect()
        except Exception:
            pass
        try:
            server.stop()
            server.destroy()
        except Exception:
            pass
        time.sleep(0.1)


class TestBehavioralCompatibility:
    """Verify behavioral compatibility with expected API behavior."""

    def test_db_read_returns_bytearray(self, server_client_pair: Tuple[Server, Client]) -> None:
        """db_read() returns a bytearray."""
        server, client = server_client_pair
        result = client.db_read(1, 0, 4)
        assert isinstance(result, bytearray)
        assert len(result) == 4

    def test_db_read_returns_correct_data(self, server_client_pair: Tuple[Server, Client]) -> None:
        """db_read() returns the correct data from server memory."""
        server, client = server_client_pair
        result = client.db_read(1, 0, 2)
        assert result[0] == 0x42
        assert result[1] == 0xFF

    def test_connect_returns_self(self) -> None:
        """connect() returns the Client instance for chaining."""
        # Note: This tests the return type, not actual connection
        # The return type should be Client for method chaining
        sig = inspect.signature(Client.connect)
        # Check return annotation if available
        assert sig.return_annotation in (Client, "Client", inspect.Parameter.empty)

    def test_get_connected_returns_bool(self, server_client_pair: Tuple[Server, Client]) -> None:
        """get_connected() returns a boolean."""
        server, client = server_client_pair
        result = client.get_connected()
        assert isinstance(result, bool)
        assert result is True

    def test_disconnect_works(self, server_client_pair: Tuple[Server, Client]) -> None:
        """disconnect() properly disconnects the client."""
        server, client = server_client_pair
        assert client.get_connected() is True
        client.disconnect()
        assert client.get_connected() is False

    def test_db_write_returns_int(self, server_client_pair: Tuple[Server, Client]) -> None:
        """db_write() returns an integer (error code)."""
        server, client = server_client_pair
        result = client.db_write(1, 0, bytearray([1, 2, 3, 4]))
        assert isinstance(result, int)
        assert result == 0  # Success

    def test_delete_returns_int(self, server_client_pair: Tuple[Server, Client]) -> None:
        """delete() returns an integer (error code)."""
        server, client = server_client_pair
        result = client.delete(Block.DB, 1)
        assert isinstance(result, int)
        assert result == 0  # Success

    def test_full_upload_returns_tuple(self, server_client_pair: Tuple[Server, Client]) -> None:
        """full_upload() returns a tuple of (bytearray, int)."""
        server, client = server_client_pair
        result = client.full_upload(Block.DB, 1)
        assert isinstance(result, tuple)
        assert len(result) == 2
        assert isinstance(result[0], bytearray)
        assert isinstance(result[1], int)

    def test_get_pdu_length_returns_int(self, server_client_pair: Tuple[Server, Client]) -> None:
        """get_pdu_length() returns an integer."""
        server, client = server_client_pair
        result = client.get_pdu_length()
        assert isinstance(result, int)
        assert result > 0

    def test_error_text_returns_str(self) -> None:
        """error_text() returns a string."""
        client = Client()
        result = client.error_text(0)
        assert isinstance(result, str)


class TestAreaEnum:
    """Verify Area enum has expected values."""

    EXPECTED_AREAS = ["PE", "PA", "MK", "DB", "CT", "TM"]

    @pytest.mark.parametrize("area_name", EXPECTED_AREAS)
    def test_area_has_value(self, area_name: str) -> None:
        """Area enum has expected member."""
        assert hasattr(Area, area_name)


class TestBlockEnum:
    """Verify Block enum has expected values."""

    EXPECTED_BLOCKS = ["OB", "DB", "SDB", "FC", "SFC", "FB", "SFB"]

    @pytest.mark.parametrize("block_name", EXPECTED_BLOCKS)
    def test_block_has_value(self, block_name: str) -> None:
        """Block enum has expected member."""
        assert hasattr(Block, block_name)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
