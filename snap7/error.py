"""
S7 error handling and exception classes.

Maps S7 error codes to Python exceptions with meaningful messages.
"""

from typing import Optional, Callable, Any, Hashable
from functools import cache


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
