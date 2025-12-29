"""
API Surface Tests.

Verify that the native Python implementation:
1. Exports all expected public symbols
2. Has all expected methods with correct signatures
3. Maps all Snap7 C library functions to Python equivalents
"""

import inspect
import time
from ctypes import c_char
from typing import Generator, Tuple

import pytest

import snap7
from snap7 import Client, Server, Partner, Logo
from snap7 import Area, Block, WordLen, SrvEvent, SrvArea


# =============================================================================
# Snap7 C Function to Python Method Mapping
# =============================================================================

# Complete mapping of Snap7 C client functions to Python methods
# Based on snap7_libmain.h from the Snap7 C library
SNAP7_CLIENT_SYNC_FUNCTIONS = {
    # Connection functions
    "Cli_Create": "create",
    "Cli_Destroy": "destroy",
    "Cli_Connect": "connect",
    "Cli_ConnectTo": "connect",  # Same method, different C overload
    "Cli_Disconnect": "disconnect",
    "Cli_SetConnectionParams": "set_connection_params",
    "Cli_SetConnectionType": "set_connection_type",
    "Cli_GetConnected": "get_connected",
    # Parameter functions
    "Cli_GetParam": "get_param",
    "Cli_SetParam": "set_param",
    # Data I/O functions
    "Cli_ReadArea": "read_area",
    "Cli_WriteArea": "write_area",
    "Cli_ReadMultiVars": "read_multi_vars",
    "Cli_WriteMultiVars": "write_multi_vars",
    # Data I/O lean functions
    "Cli_DBRead": "db_read",
    "Cli_DBWrite": "db_write",
    "Cli_MBRead": "mb_read",
    "Cli_MBWrite": "mb_write",
    "Cli_EBRead": "eb_read",
    "Cli_EBWrite": "eb_write",
    "Cli_ABRead": "ab_read",
    "Cli_ABWrite": "ab_write",
    "Cli_TMRead": "tm_read",
    "Cli_TMWrite": "tm_write",
    "Cli_CTRead": "ct_read",
    "Cli_CTWrite": "ct_write",
    # Directory functions
    "Cli_ListBlocks": "list_blocks",
    "Cli_GetAgBlockInfo": "get_block_info",
    "Cli_GetPgBlockInfo": "get_pg_block_info",
    "Cli_ListBlocksOfType": "list_blocks_of_type",
    # Block functions
    "Cli_Upload": "upload",
    "Cli_FullUpload": "full_upload",
    "Cli_Download": "download",
    "Cli_Delete": "delete",
    "Cli_DBGet": "db_get",
    "Cli_DBFill": "db_fill",
    # Date/Time functions
    "Cli_GetPlcDateTime": "get_plc_datetime",
    "Cli_SetPlcDateTime": "set_plc_datetime",
    "Cli_SetPlcSystemDateTime": "set_plc_system_datetime",
    # System info functions
    "Cli_GetOrderCode": "get_order_code",
    "Cli_GetCpuInfo": "get_cpu_info",
    "Cli_GetCpInfo": "get_cp_info",
    "Cli_ReadSZL": "read_szl",
    "Cli_ReadSZLList": "read_szl_list",
    # Control functions
    "Cli_PlcHotStart": "plc_hot_start",
    "Cli_PlcColdStart": "plc_cold_start",
    "Cli_PlcStop": "plc_stop",
    "Cli_CopyRamToRom": "copy_ram_to_rom",
    "Cli_Compress": "compress",
    "Cli_GetPlcStatus": "get_cpu_state",
    # Security functions
    "Cli_GetProtection": "get_protection",
    "Cli_SetSessionPassword": "set_session_password",
    "Cli_ClearSessionPassword": "clear_session_password",
    # Low level
    "Cli_IsoExchangeBuffer": "iso_exchange_buffer",
    # Misc
    "Cli_GetExecTime": "get_exec_time",
    "Cli_GetLastError": "get_last_error",
    "Cli_GetPduLength": "get_pdu_length",
    "Cli_ErrorText": "error_text",
}

SNAP7_CLIENT_ASYNC_FUNCTIONS = {
    "Cli_AsReadArea": "as_read_area",
    "Cli_AsWriteArea": "as_write_area",
    "Cli_AsDBRead": "as_db_read",
    "Cli_AsDBWrite": "as_db_write",
    "Cli_AsMBRead": "as_mb_read",
    "Cli_AsMBWrite": "as_mb_write",
    "Cli_AsEBRead": "as_eb_read",
    "Cli_AsEBWrite": "as_eb_write",
    "Cli_AsABRead": "as_ab_read",
    "Cli_AsABWrite": "as_ab_write",
    "Cli_AsTMRead": "as_tm_read",
    "Cli_AsTMWrite": "as_tm_write",
    "Cli_AsCTRead": "as_ct_read",
    "Cli_AsCTWrite": "as_ct_write",
    "Cli_AsListBlocksOfType": "as_list_blocks_of_type",
    "Cli_AsReadSZL": "as_read_szl",
    "Cli_AsReadSZLList": "as_read_szl_list",
    "Cli_AsUpload": "as_upload",
    "Cli_AsFullUpload": "as_full_upload",
    "Cli_AsDownload": "as_download",
    "Cli_AsCopyRamToRom": "as_copy_ram_to_rom",
    "Cli_AsCompress": "as_compress",
    "Cli_AsDBGet": "as_db_get",
    "Cli_AsDBFill": "as_db_fill",
    "Cli_CheckAsCompletion": "check_as_completion",
    "Cli_WaitAsCompletion": "wait_as_completion",
    "Cli_SetAsCallback": "set_as_callback",
}

SNAP7_SERVER_FUNCTIONS = {
    "Srv_Create": "create",
    "Srv_Destroy": "destroy",
    "Srv_Start": "start",
    "Srv_StartTo": "start_to",
    "Srv_Stop": "stop",
    "Srv_RegisterArea": "register_area",
    "Srv_UnregisterArea": "unregister_area",
    "Srv_LockArea": "lock_area",
    "Srv_UnlockArea": "unlock_area",
    "Srv_GetParam": "get_param",
    "Srv_SetParam": "set_param",
    "Srv_ClearEvents": "clear_events",
    "Srv_PickEvent": "pick_event",
    "Srv_GetMask": "get_mask",
    "Srv_SetMask": "set_mask",
    "Srv_SetEventsCallback": "set_events_callback",
    "Srv_SetReadEventsCallback": "set_read_events_callback",
    "Srv_GetStatus": "get_status",
    "Srv_SetCpuStatus": "set_cpu_status",
    "Srv_EventText": "event_text",
}

SNAP7_PARTNER_FUNCTIONS = {
    "Par_Create": "create",
    "Par_Destroy": "destroy",
    "Par_Start": "start",
    "Par_StartTo": "start_to",
    "Par_Stop": "stop",
    "Par_BSend": "b_send",
    "Par_BRecv": "b_recv",
    "Par_AsBSend": "as_b_send",
    "Par_CheckAsBSendCompletion": "check_as_b_send_completion",
    "Par_WaitAsBSendCompletion": "wait_as_b_send_completion",
    "Par_CheckAsBRecvCompletion": "check_as_b_recv_completion",
    "Par_GetParam": "get_param",
    "Par_SetParam": "set_param",
    "Par_GetTimes": "get_times",
    "Par_GetStats": "get_stats",
    "Par_GetLastError": "get_last_error",
    "Par_GetStatus": "get_status",
}


# =============================================================================
# Public Export Tests
# =============================================================================


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

    def test_enums_exported(self) -> None:
        """Enums are exported from snap7."""
        assert hasattr(snap7, "Area") and snap7.Area is Area
        assert hasattr(snap7, "Block") and snap7.Block is Block
        assert hasattr(snap7, "WordLen") and snap7.WordLen is WordLen
        assert hasattr(snap7, "SrvEvent") and snap7.SrvEvent is SrvEvent
        assert hasattr(snap7, "SrvArea") and snap7.SrvArea is SrvArea

    def test_util_classes_exported(self) -> None:
        """Utility classes are exported from snap7."""
        assert hasattr(snap7, "Row")
        assert hasattr(snap7, "DB")


# =============================================================================
# C Function Mapping Tests
# =============================================================================


class TestClientSyncFunctions:
    """Verify all Snap7 C client sync functions have Python equivalents."""

    @pytest.mark.parametrize("c_func,py_method", SNAP7_CLIENT_SYNC_FUNCTIONS.items())
    def test_method_exists(self, c_func: str, py_method: str) -> None:
        """Each Snap7 C sync function has a corresponding Python method."""
        assert hasattr(Client, py_method), f"Client missing {py_method} for {c_func}"


class TestClientAsyncFunctions:
    """Verify all Snap7 C client async functions have Python equivalents."""

    @pytest.mark.parametrize("c_func,py_method", SNAP7_CLIENT_ASYNC_FUNCTIONS.items())
    def test_method_exists(self, c_func: str, py_method: str) -> None:
        """Each Snap7 C async function has a corresponding Python method."""
        assert hasattr(Client, py_method), f"Client missing {py_method} for {c_func}"


class TestServerFunctions:
    """Verify all Snap7 C server functions have Python equivalents."""

    @pytest.mark.parametrize("c_func,py_method", SNAP7_SERVER_FUNCTIONS.items())
    def test_method_exists(self, c_func: str, py_method: str) -> None:
        """Each Snap7 C server function has a corresponding Python method."""
        assert hasattr(Server, py_method), f"Server missing {py_method} for {c_func}"


class TestPartnerFunctions:
    """Verify all Snap7 C partner functions have Python equivalents."""

    @pytest.mark.parametrize("c_func,py_method", SNAP7_PARTNER_FUNCTIONS.items())
    def test_method_exists(self, c_func: str, py_method: str) -> None:
        """Each Snap7 C partner function has a corresponding Python method."""
        assert hasattr(Partner, py_method), f"Partner missing {py_method} for {c_func}"


class TestLogoMethods:
    """Verify Logo class has expected methods."""

    @pytest.mark.parametrize("method_name", ["connect", "disconnect", "read", "write"])
    def test_method_exists(self, method_name: str) -> None:
        """Logo class has expected method."""
        assert hasattr(Logo, method_name), f"Logo missing method: {method_name}"


# =============================================================================
# Method Signature Tests
# =============================================================================


class TestMethodSignatures:
    """Verify key method signatures are correct."""

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


# =============================================================================
# Enum Value Tests
# =============================================================================


class TestEnumValues:
    """Verify enums have expected values."""

    @pytest.mark.parametrize("area_name", ["PE", "PA", "MK", "DB", "CT", "TM"])
    def test_area_values(self, area_name: str) -> None:
        """Area enum has expected members."""
        assert hasattr(Area, area_name)

    @pytest.mark.parametrize("block_name", ["OB", "DB", "SDB", "FC", "SFC", "FB", "SFB"])
    def test_block_values(self, block_name: str) -> None:
        """Block enum has expected members."""
        assert hasattr(Block, block_name)


# =============================================================================
# Coverage Summary Test
# =============================================================================


class TestCoverageSummary:
    """Summary of Snap7 C function coverage."""

    def test_total_coverage(self) -> None:
        """All Snap7 C functions are implemented."""
        total = (
            len(SNAP7_CLIENT_SYNC_FUNCTIONS)
            + len(SNAP7_CLIENT_ASYNC_FUNCTIONS)
            + len(SNAP7_SERVER_FUNCTIONS)
            + len(SNAP7_PARTNER_FUNCTIONS)
        )

        implemented = (
            sum(1 for _, m in SNAP7_CLIENT_SYNC_FUNCTIONS.items() if hasattr(Client, m))
            + sum(1 for _, m in SNAP7_CLIENT_ASYNC_FUNCTIONS.items() if hasattr(Client, m))
            + sum(1 for _, m in SNAP7_SERVER_FUNCTIONS.items() if hasattr(Server, m))
            + sum(1 for _, m in SNAP7_PARTNER_FUNCTIONS.items() if hasattr(Partner, m))
        )

        assert implemented == total, f"Coverage: {implemented}/{total}"


# =============================================================================
# Behavioral Tests (with server)
# =============================================================================


@pytest.fixture
def server_client() -> Generator[Tuple[Server, Client], None, None]:
    """Fixture that provides a connected server and client."""
    server = Server()
    port = 11102

    db_data = bytearray(100)
    db_data[0] = 0x42
    db_data[1] = 0xFF

    db_array = (c_char * 100).from_buffer(db_data)
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


class TestBehavioralAPI:
    """Verify API methods return expected types."""

    def test_db_read_returns_bytearray(self, server_client: Tuple[Server, Client]) -> None:
        """db_read() returns a bytearray."""
        _, client = server_client
        result = client.db_read(1, 0, 4)
        assert isinstance(result, bytearray)
        assert len(result) == 4

    def test_get_connected_returns_bool(self, server_client: Tuple[Server, Client]) -> None:
        """get_connected() returns a boolean."""
        _, client = server_client
        assert isinstance(client.get_connected(), bool)
        assert client.get_connected() is True

    def test_db_write_returns_int(self, server_client: Tuple[Server, Client]) -> None:
        """db_write() returns an integer."""
        _, client = server_client
        result = client.db_write(1, 0, bytearray([1, 2, 3, 4]))
        assert isinstance(result, int)
        assert result == 0

    def test_delete_returns_int(self, server_client: Tuple[Server, Client]) -> None:
        """delete() returns an integer."""
        _, client = server_client
        result = client.delete(Block.DB, 1)
        assert isinstance(result, int)

    def test_full_upload_returns_tuple(self, server_client: Tuple[Server, Client]) -> None:
        """full_upload() returns (bytearray, int)."""
        _, client = server_client
        result = client.full_upload(Block.DB, 1)
        assert isinstance(result, tuple)
        assert isinstance(result[0], bytearray)
        assert isinstance(result[1], int)

    def test_error_text_returns_str(self) -> None:
        """error_text() returns a string."""
        client = Client()
        assert isinstance(client.error_text(0), str)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
