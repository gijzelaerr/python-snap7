"""Parsers for S7 System Status List (SZL) records.

The SZL is the Siemens mechanism for reading diagnostic and identification
data from an S7 CPU. Each SZL ID has its own record layout. These helpers
take a parsed :class:`~snap7.type.S7SZL` and decode it into the
corresponding typed structure.

Both :class:`snap7.client.Client` and :class:`snap7.async_client.AsyncClient`
use these helpers so offset and field fixes only have to be made in one
place (see discussion #700).
"""

from __future__ import annotations

import struct

from .type import S7CpInfo, S7CpuInfo, S7OrderCode, S7Protection, S7SZL


def _szl_data(szl: S7SZL) -> bytes:
    """Extract the raw byte payload from an SZL response.

    ``S7SZL.Data`` is an array of ``c_byte`` (signed), which means values
    with the high bit set come through as negative Python ints. Calling
    ``bytes()`` on them raises ``ValueError``, and ``struct.unpack``
    produces wrong uint16s. Mask each byte to ``0..255`` once here so
    callers can slice, struct-unpack, and assign to ctypes char fields
    freely. Returning ``bytes`` (not ``bytearray``) matches what ctypes
    ``Structure`` char-array fields expect.
    """
    return bytes(b & 0xFF for b in szl.Data[: szl.Header.LengthDR])


def parse_cpu_info_szl(szl: S7SZL) -> S7CpuInfo:
    """Decode SZL 0x001C (component identification) into an :class:`S7CpuInfo`.

    Field offsets are relative to the start of the SZL data buffer and
    match the layout produced by real S7-300/1500 CPUs. See PR #692 for
    the offset correction and discussion #700 for context on the async
    follow-up that made these helpers necessary.
    """
    info = S7CpuInfo()
    data = _szl_data(szl)

    if len(data) >= 30:
        info.ASName = data[6:30].rstrip(b"\x00")
    if len(data) >= 64:
        info.ModuleName = data[40:64].rstrip(b"\x00")
    if len(data) >= 134:
        info.Copyright = data[108:134].rstrip(b"\x00")
    if len(data) >= 166:
        info.SerialNumber = data[142:166].rstrip(b"\x00")
    if len(data) >= 208:
        info.ModuleTypeName = data[176:208].rstrip(b"\x00")

    return info


def parse_cp_info_szl(szl: S7SZL) -> S7CpInfo:
    """Decode SZL 0x0131 (communication processor info) into an :class:`S7CpInfo`.

    Layout: four big-endian ``uint16`` fields.
    """
    info = S7CpInfo()
    data = _szl_data(szl)

    if len(data) >= 2:
        info.MaxPduLength = struct.unpack(">H", data[0:2])[0]
    if len(data) >= 4:
        info.MaxConnections = struct.unpack(">H", data[2:4])[0]
    if len(data) >= 6:
        info.MaxMpiRate = struct.unpack(">H", data[4:6])[0]
    if len(data) >= 8:
        info.MaxBusRate = struct.unpack(">H", data[6:8])[0]

    return info


def _parse_order_code_structured(data: bytes, record_len: int, ndr: int, order_code: S7OrderCode) -> bool:
    """Try parsing SZL 0x0011 as structured indexed records (S7-1200/1500).

    Returns True if at least one known record ID was found.

    Record priority (confirmed by Siemens docs and real-hardware testing):

    - **0x0007** — installed firmware version (matches TIA Portal).
      Always preferred when present.  Verified on S7-1516F (V2.9.2),
      S7-1510SP F-1 (V3.0.3), S7-1214C (V4.6.0), S7-318 (V3.2.4).
    - **0x0081** — boot loader version. Ignored — it does not reflect
      the installed firmware (e.g. reports V3.3.0 when firmware is
      V2.9.2, or V34.9.9 on S7-300).
    - **0x0001 / 0x0002** — catalog entry; used as a last-resort
      fallback only when 0x0007 is absent.
    """
    found_structured = False
    has_0x0007 = False
    offset = 4
    for _ in range(ndr):
        rec = data[offset : offset + record_len]
        if len(rec) < 2:
            break

        record_id = struct.unpack(">H", rec[0:2])[0]

        if record_id == 0x0001 and record_len >= 22:
            found_structured = True
            order_code.OrderCode = rec[2:22].rstrip(b"\x00")
            if record_len >= 26 and not has_0x0007 and (rec[23] != 0 or rec[24] != 0):
                order_code.V1, order_code.V2, order_code.V3 = rec[23], rec[24], rec[25]

        elif record_id == 0x0002 and record_len >= 26 and order_code.V1 == 0 and not has_0x0007:
            found_structured = True
            order_code.V1, order_code.V2, order_code.V3 = rec[23], rec[24], rec[25]

        elif record_id == 0x0007 and record_len >= 28:
            found_structured = True
            order_code.V1, order_code.V2, order_code.V3 = rec[-3], rec[-2], rec[-1]
            has_0x0007 = True

        elif record_id == 0x0081:
            # Boot loader — skip. Does not reflect installed firmware.
            found_structured = True

        offset += record_len

    return found_structured


def _parse_order_code_flat(data: bytes, order_code: S7OrderCode) -> None:
    """Fall back to flat-text parsing for S7-300 style payloads.

    S7-300 CPUs return SZL 0x0011 as a continuous ASCII text stream without
    structured record IDs.  The MLFB is found by searching for "6ES7" and
    the version is extracted from the 3 bytes following the 20-byte MLFB
    and a 1-byte separator (matching the S7OrderCode struct layout).
    """
    payload = data[4:]
    mlfb_start = payload.find(b"6ES7")
    if mlfb_start < 0:
        return

    if len(payload) >= mlfb_start + 20:
        order_code.OrderCode = payload[mlfb_start : mlfb_start + 20].rstrip(b"\x00 ")

    ver_offset = mlfb_start + 21
    if len(payload) >= ver_offset + 3:
        order_code.V1, order_code.V2, order_code.V3 = payload[ver_offset], payload[ver_offset + 1], payload[ver_offset + 2]


def parse_order_code_szl(szl: S7SZL) -> S7OrderCode:
    """Decode SZL 0x0011 (module order code + firmware version) into :class:`S7OrderCode`.

    Real PLCs prepend a 4-byte partial-list header (LengthDR + NDR) followed
    by variable-length records whose layout differs by PLC generation:

    **S7-1200/1500** (structured records with 2-byte index prefix):

    - 0x0001: main catalog code (MLFB) — version at fixed offsets 23/24/25
    - 0x0002: legacy firmware block (fallback, same fixed offsets)
    - 0x0007: installed firmware — always preferred (matches TIA Portal)
    - 0x0081: boot loader version — ignored (does not reflect firmware)

    **S7-300** (flat ASCII text stream, no record IDs):

    Records contain continuous text (e.g. "CPU 315-2 PN/DP...6ES7...").
    The MLFB is located by searching for "6ES7" and the version follows
    at a fixed offset from the MLFB start.

    .. note:: This is a **breaking change** from python-snap7 2.x, which
       returned the boot loader version (record 0x0081) on S7-1500. That
       version does not match the installed firmware shown in TIA Portal.
       Confirmed by Siemens documentation and real-hardware testing on
       S7-1516F, S7-1510SP, S7-1214C, and S7-318.
    """
    order_code = S7OrderCode()
    data = _szl_data(szl)

    if len(data) < 4:
        return order_code

    record_len = struct.unpack(">H", data[0:2])[0]
    ndr = struct.unpack(">H", data[2:4])[0]

    if record_len < 22 or ndr < 1 or 4 + record_len * ndr > len(data):
        return order_code

    if not _parse_order_code_structured(data, record_len, ndr, order_code):
        _parse_order_code_flat(data, order_code)

    return order_code


def parse_protection_szl(szl: S7SZL) -> S7Protection:
    """Decode SZL 0x0232 (protection level) into an :class:`S7Protection`.

    Layout: five big-endian ``uint16`` fields.
    """
    protection = S7Protection()
    data = _szl_data(szl)

    if len(data) >= 2:
        protection.sch_schal = struct.unpack(">H", data[0:2])[0]
    if len(data) >= 4:
        protection.sch_par = struct.unpack(">H", data[2:4])[0]
    if len(data) >= 6:
        protection.sch_rel = struct.unpack(">H", data[4:6])[0]
    if len(data) >= 8:
        protection.bart_sch = struct.unpack(">H", data[6:8])[0]
    if len(data) >= 10:
        protection.anl_sch = struct.unpack(">H", data[8:10])[0]

    return protection
