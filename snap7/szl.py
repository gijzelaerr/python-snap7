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


def parse_order_code_szl(szl: S7SZL) -> S7OrderCode:
    """Decode SZL 0x0011 (module order code + firmware version) into :class:`S7OrderCode`."""
    order_code = S7OrderCode()
    data = _szl_data(szl)

    if len(data) >= 20:
        order_code.OrderCode = data[0:20].rstrip(b"\x00")
    if len(data) >= 21:
        order_code.V1 = data[20]
    if len(data) >= 22:
        order_code.V2 = data[21]
    if len(data) >= 23:
        order_code.V3 = data[22]

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
