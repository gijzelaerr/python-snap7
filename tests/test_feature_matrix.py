"""
Feature Matrix Tests.

Document and verify coverage of all Snap7 C library functions in the
pure Python implementation. Maps each C function to its Python equivalent.
"""

import pytest

from snap7 import Client, Server, Partner


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
    # Note: SetRWAreaCallback not implemented in pure Python
    "Srv_GetStatus": "get_status",
    "Srv_SetCpuStatus": "set_cpu_status",
    "Srv_EventText": "event_text",
    # Note: Srv_ErrorText maps to error module, not Server method
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
    # Note: Par_SetSendCallback and Par_SetRecvCallback have different implementations
    "Par_GetParam": "get_param",
    "Par_SetParam": "set_param",
    "Par_GetTimes": "get_times",
    "Par_GetStats": "get_stats",
    "Par_GetLastError": "get_last_error",
    "Par_GetStatus": "get_status",
    # Note: Par_ErrorText maps to error module, not Partner method
}


class TestClientSyncFeatureMatrix:
    """Verify all Snap7 C client sync functions have Python equivalents."""

    @pytest.mark.parametrize("c_func,py_method", SNAP7_CLIENT_SYNC_FUNCTIONS.items())
    def test_client_sync_method_exists(self, c_func: str, py_method: str) -> None:
        """Each Snap7 C sync function has a corresponding Python method."""
        assert hasattr(Client, py_method), f"Client missing method {py_method} for C function {c_func}"


class TestClientAsyncFeatureMatrix:
    """Verify all Snap7 C client async functions have Python equivalents."""

    @pytest.mark.parametrize("c_func,py_method", SNAP7_CLIENT_ASYNC_FUNCTIONS.items())
    def test_client_async_method_exists(self, c_func: str, py_method: str) -> None:
        """Each Snap7 C async function has a corresponding Python method."""
        assert hasattr(Client, py_method), f"Client missing method {py_method} for C function {c_func}"


class TestServerFeatureMatrix:
    """Verify all Snap7 C server functions have Python equivalents."""

    @pytest.mark.parametrize("c_func,py_method", SNAP7_SERVER_FUNCTIONS.items())
    def test_server_method_exists(self, c_func: str, py_method: str) -> None:
        """Each Snap7 C server function has a corresponding Python method."""
        assert hasattr(Server, py_method), f"Server missing method {py_method} for C function {c_func}"


class TestPartnerFeatureMatrix:
    """Verify all Snap7 C partner functions have Python equivalents."""

    @pytest.mark.parametrize("c_func,py_method", SNAP7_PARTNER_FUNCTIONS.items())
    def test_partner_method_exists(self, c_func: str, py_method: str) -> None:
        """Each Snap7 C partner function has a corresponding Python method."""
        assert hasattr(Partner, py_method), f"Partner missing method {py_method} for C function {c_func}"


class TestFeatureCoverage:
    """Summary tests for feature coverage."""

    def test_client_sync_coverage_count(self) -> None:
        """Count of implemented client sync functions."""
        implemented = sum(1 for _, method in SNAP7_CLIENT_SYNC_FUNCTIONS.items() if hasattr(Client, method))
        total = len(SNAP7_CLIENT_SYNC_FUNCTIONS)
        assert implemented == total, f"Client sync: {implemented}/{total} functions implemented"
        print(f"Client sync functions: {implemented}/{total} (100%)")

    def test_client_async_coverage_count(self) -> None:
        """Count of implemented client async functions."""
        implemented = sum(1 for _, method in SNAP7_CLIENT_ASYNC_FUNCTIONS.items() if hasattr(Client, method))
        total = len(SNAP7_CLIENT_ASYNC_FUNCTIONS)
        assert implemented == total, f"Client async: {implemented}/{total} functions implemented"
        print(f"Client async functions: {implemented}/{total} (100%)")

    def test_server_coverage_count(self) -> None:
        """Count of implemented server functions."""
        implemented = sum(1 for _, method in SNAP7_SERVER_FUNCTIONS.items() if hasattr(Server, method))
        total = len(SNAP7_SERVER_FUNCTIONS)
        assert implemented == total, f"Server: {implemented}/{total} functions implemented"
        print(f"Server functions: {implemented}/{total} (100%)")

    def test_partner_coverage_count(self) -> None:
        """Count of implemented partner functions."""
        implemented = sum(1 for _, method in SNAP7_PARTNER_FUNCTIONS.items() if hasattr(Partner, method))
        total = len(SNAP7_PARTNER_FUNCTIONS)
        assert implemented == total, f"Partner: {implemented}/{total} functions implemented"
        print(f"Partner functions: {implemented}/{total} (100%)")

    def test_total_coverage(self) -> None:
        """Total feature coverage across all components."""
        total_functions = (
            len(SNAP7_CLIENT_SYNC_FUNCTIONS)
            + len(SNAP7_CLIENT_ASYNC_FUNCTIONS)
            + len(SNAP7_SERVER_FUNCTIONS)
            + len(SNAP7_PARTNER_FUNCTIONS)
        )

        client_sync = sum(1 for _, m in SNAP7_CLIENT_SYNC_FUNCTIONS.items() if hasattr(Client, m))
        client_async = sum(1 for _, m in SNAP7_CLIENT_ASYNC_FUNCTIONS.items() if hasattr(Client, m))
        server = sum(1 for _, m in SNAP7_SERVER_FUNCTIONS.items() if hasattr(Server, m))
        partner = sum(1 for _, m in SNAP7_PARTNER_FUNCTIONS.items() if hasattr(Partner, m))

        total_implemented = client_sync + client_async + server + partner

        coverage_pct = (total_implemented / total_functions) * 100
        print(f"\nTotal Snap7 C Function Coverage: {total_implemented}/{total_functions} ({coverage_pct:.1f}%)")
        print(f"  - Client Sync: {client_sync}/{len(SNAP7_CLIENT_SYNC_FUNCTIONS)}")
        print(f"  - Client Async: {client_async}/{len(SNAP7_CLIENT_ASYNC_FUNCTIONS)}")
        print(f"  - Server: {server}/{len(SNAP7_SERVER_FUNCTIONS)}")
        print(f"  - Partner: {partner}/{len(SNAP7_PARTNER_FUNCTIONS)}")

        assert total_implemented == total_functions, "Not all Snap7 C functions are implemented"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
