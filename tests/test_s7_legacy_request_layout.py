"""Legacy substreamed request and challenge regressions from issue #872."""

import hashlib
import hmac
import struct
from unittest.mock import MagicMock

import pytest

from snap7.error import S7ConnectionError
from s7commplus.codec import encode_header
from s7commplus.connection import S7CommPlusConnection
from s7commplus.protocol import FunctionCode, ProtocolVersion


def test_v1_substreamed_request_matches_accepted_tia_packet() -> None:
    # Issue #872: s7-1500.pcapng frame 94, without its session-specific HMAC.
    # Session ID / sequence / qualifier / integrity ID match that capture.
    expected = bytes.fromhex(
        "310000058600000003000003b334"
        "000003b3200401822c"
        "000004e88969001200000000896a001300896b000400000001"
        "01"  # IntegrityId, immediately after ObjectQualifier
        "00000000"
    )
    conn = S7CommPlusConnection("127.0.0.1")
    conn._session_id = 0x3B3
    conn._sequence_number = 3  # request header sequence from the same frame
    payload = conn._build_get_var_substreamed(0x3B3, 300)
    conn._connected = True
    conn._session_key = bytes(range(24))
    conn._with_integrity_id = True
    conn._integrity_id_read = 1
    conn._send_s7_data = MagicMock()
    body = struct.pack(">BHHHHB", 0x32, 0, FunctionCode.GET_VAR_SUBSTREAMED, 0, 3, 0x34) + bytes(4)
    response_digest = hmac.new(conn._session_key, body, hashlib.sha256).digest()
    protected_body = bytes([len(response_digest)]) + response_digest + body
    conn._recv_s7_data = MagicMock(return_value=encode_header(ProtocolVersion.V3, len(protected_body)) + protected_body)
    conn.send_request(FunctionCode.GET_VAR_SUBSTREAMED, payload)
    frame = conn._send_s7_data.call_args.args[0]
    assert frame[37:-4] == expected
    assert frame[5:37] == hmac.new(bytes(range(24)), expected, hashlib.sha256).digest()
    assert len(frame) + 7 == 101  # includes TPKT + COTP, as in the capture


@pytest.mark.parametrize(
    "response",
    [b"\x01", b"", b"\x00\x00\x10\x02\x01\x42\x00", bytes.fromhex("00000000000002fb00000000000000000000001700009d6c00000000")],
)
def test_failed_legacy_challenge_does_not_reuse_createobject_challenge(response: bytes) -> None:
    conn = S7CommPlusConnection("127.0.0.1")
    conn._session_challenge = bytes(range(20))
    conn.send_request = MagicMock(return_value=response)
    with pytest.raises(S7ConnectionError):
        conn._post_auth_legitimation()
    conn.send_request.assert_called_once()


def test_legacy_legitimation_uses_the_new_challenge(monkeypatch: pytest.MonkeyPatch) -> None:
    challenge = bytes(range(20))
    conn = S7CommPlusConnection("127.0.0.1")
    conn._session_challenge = b"old challenge value!"
    conn._session_key = bytes(range(24))
    response = b"\x00\x00\x10\x02\x14" + challenge + b"\x00"
    conn.send_request = MagicMock(side_effect=[response, b"\x00"])
    solve = MagicMock(return_value=bytes(248))
    monkeypatch.setattr("s7commplus.session_auth.legitimate.solve_legitimate_challenge_real_plc", solve)
    conn._post_auth_legitimation("password")
    assert solve.call_args.args[0] == challenge
    assert solve.call_args.args[-1] == "password"
    assert conn.send_request.call_count == 2
