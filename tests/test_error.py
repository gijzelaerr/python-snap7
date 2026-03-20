"""Tests for snap7.error module — error routing, check_error(), error_wrap() decorator."""

import pytest

from snap7.error import (
    S7Error,
    S7ConnectionError,
    S7ProtocolError,
    S7TimeoutError,
    S7AuthenticationError,
    S7StalePacketError,
    S7PacketLostError,
    get_error_message,
    get_protocol_error_message,
    check_error,
    error_text,
    error_wrap,
)


class TestExceptionClasses:
    """Verify all exception classes can be instantiated with expected attributes."""

    def test_s7error_with_code(self) -> None:
        err = S7Error("msg", error_code=42)
        assert str(err) == "msg"
        assert err.error_code == 42

    def test_s7error_without_code(self) -> None:
        err = S7Error("msg")
        assert err.error_code is None

    def test_subclass_hierarchy(self) -> None:
        assert issubclass(S7ConnectionError, S7Error)
        assert issubclass(S7ProtocolError, S7Error)
        assert issubclass(S7TimeoutError, S7Error)
        assert issubclass(S7AuthenticationError, S7Error)
        assert issubclass(S7StalePacketError, S7ProtocolError)
        assert issubclass(S7PacketLostError, S7ProtocolError)

    def test_all_subclasses_instantiate(self) -> None:
        for cls in (
            S7ConnectionError,
            S7ProtocolError,
            S7TimeoutError,
            S7AuthenticationError,
            S7StalePacketError,
            S7PacketLostError,
        ):
            e = cls("test", error_code=1)
            assert str(e) == "test"
            assert e.error_code == 1


class TestGetErrorMessage:
    """Tests for get_error_message() — known and unknown codes."""

    def test_success_code(self) -> None:
        assert get_error_message(0x00000000) == "Success"

    def test_known_client_error(self) -> None:
        # Use a code unique to client errors (not overlapping with server: 0x009+)
        assert get_error_message(0x00900000) == "errCliAddressOutOfRange"

    def test_known_isotcp_error(self) -> None:
        assert get_error_message(0x00010000) == "errIsoConnect"

    def test_known_server_error(self) -> None:
        assert get_error_message(0x00200000) == "errSrvDBNullPointer"

    def test_unknown_code(self) -> None:
        msg = get_error_message(0xDEADBEEF)
        assert "Unknown error" in msg
        assert "0xdeadbeef" in msg


class TestGetProtocolErrorMessage:
    """Tests for get_protocol_error_message() — known and unknown protocol codes."""

    def test_known_protocol_code(self) -> None:
        assert get_protocol_error_message(0x0000) == "No error"

    def test_known_protocol_error(self) -> None:
        assert "block number" in get_protocol_error_message(0x0110).lower()

    def test_unknown_protocol_code(self) -> None:
        msg = get_protocol_error_message(0xFFFF)
        assert "Unknown protocol error" in msg


class TestErrorText:
    """Tests for error_text() with different contexts."""

    def test_client_context(self) -> None:
        msg = error_text(0x00100000, "client")
        assert msg == "errNegotiatingPDU"

    def test_server_context(self) -> None:
        # Server dict has its own 0x00100000 entry
        msg = error_text(0x00100000, "server")
        assert msg == "errSrvCannotStart"

    def test_partner_context(self) -> None:
        # Partner uses client errors
        msg = error_text(0x00100000, "partner")
        assert msg == "errNegotiatingPDU"

    def test_unknown_context_falls_back_to_client(self) -> None:
        msg = error_text(0x00100000, "unknown_context")
        assert msg == "errNegotiatingPDU"

    def test_unknown_error_code(self) -> None:
        msg = error_text(0xBADC0DE, "client")
        assert "Unknown error" in msg

    def test_caching(self) -> None:
        # Calling twice should return the same cached result
        a = error_text(0x00100000, "client")
        b = error_text(0x00100000, "client")
        assert a == b


class TestCheckError:
    """Tests for check_error() — routes error codes to exception types."""

    def test_zero_returns_none(self) -> None:
        # Should not raise
        check_error(0)

    def test_iso_connect_raises_connection_error(self) -> None:
        with pytest.raises(S7ConnectionError):
            check_error(0x00010000)

    def test_iso_disconnect_raises_connection_error(self) -> None:
        with pytest.raises(S7ConnectionError):
            check_error(0x00020000)

    def test_timeout_raises_timeout_error(self) -> None:
        with pytest.raises(S7TimeoutError):
            check_error(0x02000000)

    def test_other_isotcp_raises_connection_error(self) -> None:
        with pytest.raises(S7ConnectionError):
            check_error(0x00030000)  # errIsoInvalidPDU

    def test_generic_error_raises_runtime_error(self) -> None:
        with pytest.raises(RuntimeError):
            check_error(0x00100000)  # errNegotiatingPDU (client error)


class TestErrorWrap:
    """Tests for error_wrap() decorator."""

    def test_no_error(self) -> None:
        @error_wrap("client")
        def ok_func() -> int:
            return 0

        # Should not raise, returns None (decorator suppresses return value)
        result = ok_func()
        assert result is None

    def test_raises_on_error(self) -> None:
        @error_wrap("client")
        def bad_func() -> int:
            return 0x02000000  # timeout

        with pytest.raises(S7TimeoutError):
            bad_func()

    def test_passes_args_through(self) -> None:
        @error_wrap("client")
        def func_with_args(a: int, b: int) -> int:
            return a + b

        # 0 + 0 = 0, no error
        func_with_args(0, 0)

        with pytest.raises(RuntimeError):
            # Non-zero = error
            func_with_args(0x00100000, 0)
