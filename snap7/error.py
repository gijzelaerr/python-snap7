"""
S7 error handling and exception classes.

Maps S7 error codes to Python exceptions with meaningful messages.
"""

from typing import Optional, Callable, Any, Hashable

from .compat import cache


class S7Error(Exception):
    """Base exception for all S7 protocol errors."""

    def __init__(self, message: str, error_code: Optional[int] = None):
        super().__init__(message)
        self.error_code = error_code


class S7ConnectionError(S7Error):
    """Raised when connection to S7 device fails."""

    pass


class S7ProtocolError(S7Error):
    """Raised when S7 protocol communication fails."""

    pass


class S7TimeoutError(S7Error):
    """Raised when S7 operation times out."""

    pass


class S7AuthenticationError(S7Error):
    """Raised when S7 authentication fails."""

    pass


# S7 client error codes
s7_client_errors = {
    0x00100000: "errNegotiatingPDU",
    0x00200000: "errCliInvalidParams",
    0x00300000: "errCliJobPending",
    0x00400000: "errCliTooManyItems",
    0x00500000: "errCliInvalidWordLen",
    0x00600000: "errCliPartialDataWritten",
    0x00700000: "errCliSizeOverPDU",
    0x00800000: "errCliInvalidPlcAnswer",
    0x00900000: "errCliAddressOutOfRange",
    0x00A00000: "errCliInvalidTransportSize",
    0x00B00000: "errCliWriteDataSizeMismatch",
    0x00C00000: "errCliItemNotAvailable",
    0x00D00000: "errCliInvalidValue",
    0x00E00000: "errCliCannotStartPLC",
    0x00F00000: "errCliAlreadyRun",
    0x01000000: "errCliCannotStopPLC",
    0x01100000: "errCliCannotCopyRamToRom",
    0x01200000: "errCliCannotCompress",
    0x01300000: "errCliAlreadyStop",
    0x01400000: "errCliFunNotAvailable",
    0x01500000: "errCliUploadSequenceFailed",
    0x01600000: "errCliInvalidDataSizeRecvd",
    0x01700000: "errCliInvalidBlockType",
    0x01800000: "errCliInvalidBlockNumber",
    0x01900000: "errCliInvalidBlockSize",
    0x01A00000: "errCliDownloadSequenceFailed",
    0x01B00000: "errCliInsertRefused",
    0x01C00000: "errCliDeleteRefused",
    0x01D00000: "errCliNeedPassword",
    0x01E00000: "errCliInvalidPassword",
    0x01F00000: "errCliNoPasswordToSetOrClear",
    0x02000000: "errCliJobTimeout",
    0x02100000: "errCliPartialDataRead",
    0x02200000: "errCliBufferTooSmall",
    0x02300000: "errCliFunctionRefused",
    0x02400000: "errCliDestroying",
    0x02500000: "errCliInvalidParamNumber",
    0x02600000: "errCliCannotChangeParam",
}

isotcp_errors = {
    0x00010000: "errIsoConnect",
    0x00020000: "errIsoDisconnect",
    0x00030000: "errIsoInvalidPDU",
    0x00040000: "errIsoInvalidDataSize",
    0x00050000: "errIsoNullPointer",
    0x00060000: "errIsoShortPacket",
    0x00070000: "errIsoTooManyFragments",
    0x00080000: "errIsoPduOverflow",
    0x00090000: "errIsoSendPacket",
    0x000A0000: "errIsoRecvPacket",
    0x000B0000: "errIsoInvalidParams",
}

tcp_errors = {
    0x00000001: "evcServerStarted",
    0x00000002: "evcServerStopped",
    0x00000004: "evcListenerCannotStart",
    0x00000008: "evcClientAdded",
    0x00000010: "evcClientRejected",
    0x00000020: "evcClientNoRoom",
    0x00000040: "evcClientException",
    0x00000080: "evcClientDisconnected",
    0x00000100: "evcClientTerminated",
    0x00000200: "evcClientsDropped",
}

s7_server_errors = {
    0x00100000: "errSrvCannotStart",
    0x00200000: "errSrvDBNullPointer",
    0x00300000: "errSrvAreaAlreadyExists",
    0x00400000: "errSrvUnknownArea",
    0x00500000: "errSrvInvalidParams",
    0x00600000: "errSrvTooManyDB",
    0x00700000: "errSrvInvalidParamNumber",
    0x00800000: "errSrvCannotChangeParam",
}

# S7 protocol-level error codes (from Wireshark S7 dissector)
# These cover USERDATA parameter errors, protocol errors, and resource errors
# that occur during real PLC communication.
# Source: https://github.com/wireshark/wireshark/blob/master/epan/dissectors/packet-s7comm.c
S7_PROTOCOL_ERROR_CODES = {
    0x0000: "No error",
    0x0110: "Invalid block number",
    0x0111: "Invalid request length",
    0x0112: "Invalid parameter",
    0x0113: "Invalid block type",
    0x0114: "Block not found",
    0x0115: "Block already exists",
    0x0116: "Block is write-protected",
    0x0117: "The block/operating system update is too large",
    0x0118: "Invalid block number",
    0x0119: "Incorrect password entered",
    0x011A: "PG resource error",
    0x011B: "PLC resource error",
    0x011C: "Protocol error",
    0x011D: "Too many blocks (module-related restriction)",
    0x011E: "There is no longer a connection to the database, or S7DOS handle is invalid",
    0x011F: "Result buffer too small",
    0x0120: "End of block list",
    0x0140: "Insufficient memory available",
    0x0141: "Job cannot be processed because of a lack of resources",
    0x8001: "The requested service cannot be performed while the block is in the current status",
    0x8003: "S7 protocol error: Error occurred while transferring the block",
    0x8100: "Application, general error: Service unknown to remote module",
    0x8104: "This service is not implemented on the module or a frame error was reported",
    0x8204: "The type specification for the object is inconsistent",
    0x8205: "A copied block already exists and is not linked",
    0x8301: "Insufficient memory space or work memory on the module, or specified storage medium not accessible",
    0x8302: "Too few resources available or the processor resources are not available",
    0x8304: "No further parallel upload possible. There is a resource bottleneck",
    0x8305: "Function not available",
    0x8306: "Insufficient work memory (for copying, linking, loading AWP)",
    0x8307: "Not enough retentive work memory (for copying, linking, loading AWP)",
    0x8401: "S7 protocol error: Invalid service sequence (for example, loading or uploading a block)",
    0x8402: "Service cannot execute owing to status of the addressed object",
    0x8404: "S7 protocol: The function cannot be performed",
    0x8405: "Remote block is in DISABLE state (CFB). The function cannot be performed",
    0x8500: "S7 protocol error: Wrong frames",
    0x8503: "Alarm from the module: Service canceled prematurely",
    0x8701: "Error addressing the object on the communications partner (for example, area length error)",
    0x8702: "The requested service is not supported by the module",
    0x8703: "Access to object refused",
    0x8704: "Access error: Object damaged",
    0xD001: "Protocol error: Illegal job number",
    0xD002: "Parameter error: Illegal job variant",
    0xD003: "Parameter error: Debugging function not supported by module",
    0xD004: "Parameter error: Illegal job status",
    0xD005: "Parameter error: Illegal job termination",
    0xD006: "Parameter error: Illegal link disconnection ID",
    0xD007: "Parameter error: Illegal number of buffer elements",
    0xD008: "Parameter error: Illegal scan rate",
    0xD009: "Parameter error: Illegal number of executions",
    0xD00A: "Parameter error: Illegal trigger event",
    0xD00B: "Parameter error: Illegal trigger condition",
    0xD011: "Parameter error in path of the call environment: Block does not exist",
    0xD012: "Parameter error: Wrong address in block",
    0xD014: "Parameter error: Block being deleted/overwritten",
    0xD015: "Parameter error: Illegal tag address",
    0xD016: "Parameter error: Test jobs not possible, because of errors in user program",
    0xD017: "Parameter error: Illegal trigger number",
    0xD025: "Parameter error: Invalid path",
    0xD026: "Parameter error: Illegal access type",
    0xD027: "Parameter error: This number of data blocks is not permitted",
    0xD031: "Internal protocol error",
    0xD032: "Parameter error: Wrong result buffer length",
    0xD033: "Protocol error: Wrong job length",
    0xD03F: "Coding error: Error in parameter section (for example, reserve bytes not equal to 0)",
    0xD041: "Data error: Illegal status list ID",
    0xD042: "Data error: Illegal tag address",
    0xD043: "Data error: Referenced job not found, check job data",
    0xD044: "Data error: Illegal tag value, check job data",
    0xD045: "Data error: Exiting the ODIS control is not allowed in HOLD",
    0xD046: "Data error: Illegal measuring stage during run-time measurement",
    0xD047: "Data error: Illegal hierarchy in 'Read job list'",
    0xD048: "Data error: Illegal deletion ID in 'Delete job'",
    0xD049: "Invalid substitute ID in 'Replace job'",
    0xD04A: "Error executing 'program status'",
    0xD05F: "Coding error: Error in data section (for example, reserve bytes not equal to 0, ...)",
    0xD061: "Resource error: No memory space for job",
    0xD062: "Resource error: Job list full",
    0xD063: "Resource error: Trigger event occupied",
    0xD064: "Resource error: Not enough memory space for one result buffer element",
    0xD065: "Resource error: Not enough memory space for several result buffer elements",
    0xD066: "Resource error: The timer available for run-time measurement is occupied by another job",
    0xD067: "Resource error: Too many 'modify tag' jobs active (in particular multi-processor operation)",
    0xD081: "Function not permitted in current mode",
    0xD082: "Mode error: Cannot exit HOLD mode",
    0xD0A1: "Function not permitted in current protection level",
    0xD0A2: "Function not possible at present, because a function is running that modifies memory",
    0xD0A3: "Too many 'modify tag' jobs active on the I/O (in particular multi-processor operation)",
    0xD0A4: "'Forcing' has already been established",
    0xD0A5: "Referenced job not found",
    0xD0A6: "Job cannot be disabled/enabled",
    0xD0A7: "Job cannot be deleted, for example because it is currently being read",
    0xD0A8: "Job cannot be replaced, for example because it is currently being read or deleted",
    0xD0A9: "Job cannot be read, for example because it is currently being deleted",
    0xD0AA: "Time limit exceeded in processing operation",
    0xD0AB: "Invalid job parameters in process operation",
    0xD0AC: "Invalid job data in process operation",
    0xD0AD: "Operating mode already set",
    0xD0AE: "The job was set up over a different connection and can only be handled over this connection",
    0xD0C1: "At least one error has been detected while accessing the tag(s)",
    0xD0C2: "Change to STOP/HOLD mode",
    0xD0C3: "At least one error was detected while accessing the tag(s). Mode change to STOP/HOLD",
    0xD0C4: "Timeout during run-time measurement",
    0xD0C5: "Display of block stack inconsistent, because blocks were deleted/reloaded",
    0xD0C6: "Job was automatically deleted as the jobs it referenced have been deleted",
    0xD0C7: "The job was automatically deleted because STOP mode was exited",
    0xD0C8: "'Block status' aborted because of inconsistencies between test job and running program",
    0xD0C9: "Exit the status area by resetting OB90",
    0xD0CA: "Exiting the status range by resetting OB90 and access error reading tags before exiting",
    0xD0CB: "The output disable for the peripheral outputs has been activated again",
    0xD0CC: "The amount of data for the debugging functions is restricted by the time limit",
    0xD201: "Syntax error in block name",
    0xD202: "Syntax error in function parameters",
    0xD205: "Linked block already exists in RAM: Conditional copying is not possible",
    0xD206: "Linked block already exists in EPROM: Conditional copying is not possible",
    0xD208: "Maximum number of copied (not linked) blocks on module exceeded",
    0xD209: "(At least) one of the given blocks not found on the module",
    0xD20A: "The maximum number of blocks that can be linked with one job was exceeded",
    0xD20B: "The maximum number of blocks that can be deleted with one job was exceeded",
    0xD20C: "OB cannot be copied because the associated priority class does not exist",
    0xD20D: "SDB cannot be interpreted (for example, unknown number)",
    0xD20E: "No (further) block available",
    0xD20F: "Module-specific maximum block size exceeded",
    0xD210: "Invalid block number",
    0xD212: "Incorrect header attribute (run-time relevant)",
    0xD213: "Too many SDBs. Note the restrictions on the module being used",
    0xD216: "Invalid user program - reset module",
    0xD217: "Protection level specified in module properties not permitted",
    0xD218: "Incorrect attribute (active/passive)",
    0xD219: "Incorrect block lengths (for example, incorrect length of first section or of the whole block)",
    0xD21A: "Incorrect local data length or write-protection code faulty",
    0xD21B: "Module cannot compress or compression was interrupted early",
    0xD21D: "The volume of dynamic project data transferred is illegal",
    0xD21E: "Unable to assign parameters to a module (such as FM, CP). The system data could not be linked",
    0xD220: "Invalid programming language. Note the restrictions on the module being used",
    0xD221: "The system data for connections or routing are not valid",
    0xD222: "The system data of the global data definition contain invalid parameters",
    0xD223: "Error in instance data block for communication function block or maximum number of instance DBs exceeded",
    0xD224: "The SCAN system data block contains invalid parameters",
    0xD225: "The DP system data block contains invalid parameters",
    0xD226: "A structural error occurred in a block",
    0xD230: "A structural error occurred in a block",
    0xD231: "At least one loaded OB cannot be copied because the associated priority class does not exist",
    0xD232: "At least one block number of a loaded block is illegal",
    0xD234: "Block exists twice in the specified memory medium or in the job",
    0xD235: "The block contains an incorrect checksum",
    0xD236: "The block does not contain a checksum",
    0xD237: "You are about to load the block twice, i.e. a block with the same time stamp already exists on the CPU",
    0xD238: "At least one of the blocks specified is not a DB",
    0xD239: "At least one of the DBs specified is not available as a linked variant in the load memory",
    0xD23A: "At least one of the specified DBs is considerably different from the copied and linked variant",
    0xD240: "Coordination rules violated",
    0xD241: "The function is not permitted in the current protection level",
    0xD242: "Protection violation while processing F blocks",
    0xD250: "Update and module ID or version do not match",
    0xD251: "Incorrect sequence of operating system components",
    0xD252: "Checksum error",
    0xD253: "No executable loader available; update only possible using a memory card",
    0xD254: "Storage error in operating system",
    0xD280: "Error compiling block in S7-300 CPU",
    0xD2A1: "Another block function or a trigger on a block is active",
    0xD2A2: "A trigger is active on a block. Complete the debugging function first",
    0xD2A3: "The block is not active (linked), the block is occupied or the block is currently marked for deletion",
    0xD2A4: "The block is already being processed by another block function",
    0xD2A6: "It is not possible to save and change the user program simultaneously",
    0xD2A7: "The block has the attribute 'unlinked' or is not processed",
    0xD2A8: "An active debugging function is preventing parameters from being assigned to the CPU",
    0xD2A9: "New parameters are being assigned to the CPU",
    0xD2AA: "New parameters are currently being assigned to the modules",
    0xD2AB: "The dynamic configuration limits are currently being changed",
    0xD2AC: "A running active or deactivate assignment (SFC 12) is temporarily preventing R-KiR process",
    0xD2B0: "An error occurred while configuring in RUN (CiR)",
    0xD2C0: "The maximum number of technological objects has been exceeded",
    0xD2C1: "The same technology data block already exists on the module",
    0xD2C2: "Downloading the user program or downloading the hardware configuration is not possible",
    0xD401: "Information function unavailable",
    0xD402: "Information function unavailable",
    0xD403: "Service has already been logged on/off (Diagnostics/PMC)",
    0xD404: "Maximum number of nodes reached. No more logons possible for diagnostics/PMC",
    0xD405: "Service not supported or syntax error in function parameters",
    0xD406: "Required information currently unavailable",
    0xD407: "Diagnostics error occurred",
    0xD408: "Update aborted",
    0xD409: "Error on DP bus",
    0xD601: "Syntax error in function parameter",
    0xD602: "Incorrect password entered",
    0xD603: "The connection has already been legitimized",
    0xD604: "The connection has already been enabled",
    0xD605: "Legitimization not possible because password does not exist",
    0xD801: "At least one tag address is invalid",
    0xD802: "Specified job does not exist",
    0xD803: "Illegal job status",
    0xD804: "Illegal cycle time (illegal time base or multiple)",
    0xD805: "No more cyclic read jobs can be set up",
    0xD806: "The referenced job is in a state in which the requested function cannot be performed",
    0xD807: "Function aborted due to overload, meaning executing the read cycle takes longer than the set scan cycle time",
    0xDC01: "Date and/or time invalid",
    0xE201: "CPU is already the master",
    0xE202: "Connect and update not possible due to different user program in flash module",
    0xE203: "Connect and update not possible due to different firmware",
    0xE204: "Connect and update not possible due to different memory configuration",
    0xE205: "Connect/update aborted due to synchronization error",
    0xE206: "Connect/update denied due to coordination violation",
    0xEF01: "S7 protocol error: Error at ID2; only 00H permitted in job",
    0xEF02: "S7 protocol error: Error at ID2; set of resources does not exist",
}


def get_protocol_error_message(code: int) -> str:
    """Get human-readable error message for an S7 protocol-level error code.

    These are the error codes found in USERDATA parameter sections and
    S7 header error_class/error_code fields. They are distinct from the
    higher-level client/ISO error codes.

    Args:
        code: S7 protocol error code (e.g., 0xD401, 0x8104)

    Returns:
        Human-readable error description, or a hex-formatted unknown message.
    """
    return S7_PROTOCOL_ERROR_CODES.get(code, f"Unknown protocol error: {code:#06x}")


class S7StalePacketError(S7ProtocolError):
    """Raised when a response has an old/stale PDU reference number."""

    pass


class S7PacketLostError(S7ProtocolError):
    """Raised when a response PDU reference is ahead of expected (packet loss)."""

    pass


# Combined error dictionaries
client_errors = s7_client_errors.copy()
client_errors.update(isotcp_errors)
client_errors.update(tcp_errors)

server_errors = s7_server_errors.copy()
server_errors.update(isotcp_errors)
server_errors.update(tcp_errors)

# All error codes combined
S7_ERROR_CODES = {
    0x00000000: "Success",
    **s7_client_errors,
    **isotcp_errors,
    **s7_server_errors,
}


def get_error_message(error_code: int) -> str:
    """Get human-readable error message for S7 error code."""
    return S7_ERROR_CODES.get(error_code, f"Unknown error: {error_code:#08x}")


@cache
def error_text(error: int, context: str = "client") -> str:
    """Returns a textual explanation of a given error number.

    Args:
        error: an error integer
        context: context in which is called from, server, client or partner

    Returns:
        The error message as a string.
    """
    errors = {"client": client_errors, "server": server_errors, "partner": client_errors}
    error_dict = errors.get(context, client_errors)
    return error_dict.get(error, f"Unknown error: {error:#08x}")


def check_error(code: int, context: str = "client") -> None:
    """Check if the error code is set. If so, raise an appropriate exception.

    Args:
        code: error code number.
        context: context in which is called.

    Raises:
        S7ConnectionError: for connection-related errors
        S7TimeoutError: for timeout errors
        S7ProtocolError: for protocol errors
        RuntimeError: for other errors (backwards compatibility)
    """
    if code == 0:
        return

    message = error_text(code, context)

    # Map to specific exception types based on error code patterns
    if code in [0x00010000, 0x00020000]:  # ISO connect/disconnect errors
        raise S7ConnectionError(message, code)
    elif code == 0x02000000:  # Job timeout
        raise S7TimeoutError(message, code)
    elif code in isotcp_errors:
        raise S7ConnectionError(message, code)
    else:
        # Use RuntimeError for backwards compatibility with existing code
        raise RuntimeError(message)


def error_wrap(context: str) -> Callable[..., Callable[..., None]]:
    """Decorator that parses an S7 error code returned by the decorated function."""

    def middle(func: Callable[..., int]) -> Any:
        def inner(*args: tuple[Any, ...], **kwargs: dict[Hashable, Any]) -> None:
            code = func(*args, **kwargs)
            check_error(code, context=context)

        return inner

    return middle
