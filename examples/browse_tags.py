"""
browse_tags.py — Read symbolic I/Q/M tags from an S7-1200 FW V4.5 PLC.

Technique: EXPLORE + decompression with a partial preset dictionary
(Adler-32 0xce9b821b, 594 of 32768 bytes reconstructed via oracle analysis).
The same FDICT is used for all three areas (I, Q, M) — confirmed on
independent Wireshark pcapng captures.

Results on S7-1200 CPU 1212C DC/DC/DC, FW V4.5 (40-tag project):
  I area (RID=80): 13/13 complete
  Q area (RID=81): 11/11 complete
  M area (RID=82):  9/15 — 6 structural gaps (see below)
Score vs TIA Portal export: 33/40 correct, 6 gap, 0 wrong.

Prerequisites:
  - python-snap7 S7CommPlus branch with Patches 1, 5, 6 applied
    (SequenceNumber field, _collect_explore_frames, session key)
  - No password, no TLS (adjust connect() call if needed)

Usage:
    python browse_tags.py           # all areas
    python browse_tags.py I         # I area only
    python browse_tags.py Q M       # Q and M

Structural limit — M area Byte/Word tags:
  The EXPLORE blob uses an identical deflate sequence for %MB and %MW
  addresses. It is not possible to distinguish them without external
  information (e.g. a TIA Portal export). The 6 affected tags show
  LogicalAddress='?' but always have correct ByteOffset values.

Tested on:
  Siemens S7-1200 CPU 1212C DC/DC/DC, firmware V4.5, IP 192.168.5.11
"""

import re
import sys
import zlib
from unittest import mock

PLC_HOST = "192.168.5.11"
PLC_PORT = 102

AREAS = {"I": 80, "Q": 81, "M": 82}


# ---------------------------------------------------------------------------
# Partial preset dictionary (594 of 32768 positions mapped, Adler-32 0xce9b821b)
# Reconstructed via oracle technique: inflate the same blob 4 times with
# DICT_ZERO, DICT_FF, DICT_A (i%256), DICT_B (i>>8). Identical bytes are
# literals; differing bytes reveal FDICT position (B_out<<8)|A_out.
# ---------------------------------------------------------------------------


def _build_fdict() -> bytes:
    d = bytearray(32768)

    def s(p, t):
        for i, c in enumerate(t.encode("latin-1")):
            d[p + i] = c

    # Root / element structure
    s(0x7FF1, "ControllerTags>")
    s(0x7CC3, '" />')
    d[0x7CC7] = ord("<")
    s(0x7CC8, "Tags")
    d[0x7CCC] = ord(" ")
    s(0x7CCD, 'HmiVisible="')
    s(0x7C0D, "/><Tags")
    s(0x7C15, "HmiVisible=")

    # 88-char Bool attribute block, split around 2-byte gap at 0x7ed6-7ed7
    # Full string: '" Comment="" HmiVisible="True" HmiAccessible="True"
    #               Retain="False" LogicalAddress="%I43.'
    b88 = b'" Comment="" HmiVisible="True" HmiAccessible="True" Retain="False" LogicalAddress="%I43.'
    for i in range(63):
        d[0x7E97 + i] = b88[i]
    for i in range(25):
        d[0x7ED8 + i] = b88[63 + i]
    s(0x7EF2, '" ByteOffset="')  # 14c — unlocks ByteOffset for M/Q Bool
    d[0x7EF1] = ord("4")  # Clock_1.25Hz bit digit → %M0.4

    # Common attribute blocks
    s(0x7BAF, 'True" HmiAccessible="True" Retain="False" Logical')
    s(0x7B8A, '" DataType="Bool" ID="')
    s(0x7B9C, 'ID="')
    s(0x7BA0, '9" HmiVisible="')
    s(0x7FE7, 'Visible="')
    s(0x7F36, 'True"')
    s(0x7F71, '" HmiAccessible="True" Retain="False" Logical')
    s(0x7FAD, ' ByteOffset="')
    d[0x7FAC] = ord('"')
    s(0x7FC5, "True")

    # LogicalAddress blocks
    s(0x7FA0, 'Address="%IW"')  # Word/Int I area
    s(0x7D62, 'lAddress="%QW" ByteOffset=2')  # Word Q area
    s(0x7BFC, '" ByteOffset="')  # Q/M Bool ByteOffset opener
    d[0x7BFB] = ord("1")  # bit '1' (Clock_5Hz, Tag_25)

    # Name blocks
    d[0x7F3B] = ord(" ")
    s(0x7F3C, 'Name="Tag_0')
    d[0x7F46] = ord("6")
    s(0x7F47, '" DataType="Bool" ')
    s(0x7B79, 'True" Name="Tag_1')  # M area Tag_1X prefix
    s(0x7E7A, "Tag_")  # M area generic Tag_ prefix
    d[0x7E7E] = ord("5")
    d[0x7E7F] = ord('"')
    s(0x7E80, ' DataType="Bool" ')
    s(0x7F17, 'utput" ')  # 'output' name suffix (Q area)
    s(0x7C3F, 'Tags Name="Tag_02" DataType="Bool" ')
    s(0x7DB3, 'Tags Name="Tag_04" DataType="Word" ')
    d[0x7D08] = ord("3")
    d[0x7D09] = ord('"')
    s(0x7D0A, ' DataType="Bool" ')

    # Clock / ID digit blocks (M area)
    d[0x7C66] = ord("1")
    d[0x7C67] = ord("2")
    s(0x7C68, '" HmiVisible="')
    s(0x7C76, 'True" HmiAccessible="True" Retain="False" Logica')
    d[0x7C0A] = ord("0")
    d[0x7CEA] = ord(" ")
    d[0x7C14] = ord(" ")
    d[0x7E96] = ord("5")
    d[0x7F00] = ord("4")
    d[0x7F01] = ord('"')
    d[0x7E37] = ord("3")
    d[0x7E38] = ord('"')
    s(0x7CC0, '="1')
    s(0x7C0A, '0" ')

    return bytes(d)


# ---------------------------------------------------------------------------
# Connection and decompression
# ---------------------------------------------------------------------------


def _fetch_area(rid: int, fdict: bytes) -> bytes | None:
    """Connect to PLC, send EXPLORE for the given RID, decompress the blob."""
    try:
        from s7._s7commplus_client import _build_explore_payload_v3
        from s7.connection import S7CommPlusConnection
        from s7.protocol import FunctionCode
    except ImportError:
        print("Error: python-snap7 not found. pip install python-snap7")
        sys.exit(1)

    with mock.patch.object(S7CommPlusConnection, "_post_auth_legitimation", return_value=None):
        conn = S7CommPlusConnection(host=PLC_HOST, port=PLC_PORT)
        conn.connect(use_tls=False, password="", timeout=5.0)
    try:
        resp = conn.send_request(FunctionCode.EXPLORE, _build_explore_payload_v3(rid))
        full = conn._collect_explore_frames(resp)
    finally:
        try:
            conn.disconnect()
        except Exception:
            pass

    p = full.find(b"\x78\x7d")
    if p < 0:
        return None
    try:
        return zlib.decompressobj(wbits=-15, zdict=fdict).decompress(full[p + 6 :])
    except zlib.error:
        return None


# ---------------------------------------------------------------------------
# Tag extraction
# ---------------------------------------------------------------------------


def _normalize_name(raw: str) -> str:
    m = re.match(r"^(Tag_)0+([0-9]+)$", raw)
    if m:
        return m.group(1) + m.group(2)
    return raw


def _extract_tags(data: bytes, area_prefix: str = "") -> list[dict]:
    """Extract tags from the decompressed XML blob.

    Unknown FDICT positions produce null bytes, shown as '?' after decoding.
    Extraction anchors on always-literal ID values, which are never stored
    in the preset dictionary and are therefore always visible in the output.

    Byte-type fallback for I/Q areas:
      Bool  -> garbled %I43.X in blob -> reconstruct %{A}{bo}.{bit}
      Word  -> %IW/%QW visible in blob -> append ByteOffset
      Byte  -> only remaining type     -> reconstruct %{A}B{ByteOffset}
    """
    text = data.replace(b"\x00", b"?").decode("latin-1")
    tags: list[dict] = []
    seen_id: set[str] = set()
    seen_name: set[str] = set()
    _synthetic = 0

    for m in re.finditer(r'ID="([0-9?]{1,6})[?"]', text):
        raw_id = m.group(1)
        leading = re.match(r"^([0-9]+)", raw_id)
        if leading:
            tag_id = leading.group(1)
            if tag_id in seen_id:
                continue
            seen_id.add(tag_id)
        else:
            tag_id = f"?{_synthetic}"
            _synthetic += 1

        pos = m.start()
        anchors = [a.start() for a in re.finditer(r'<Tags|Visible="', text[:pos])]
        start = anchors[-1] if anchors else max(0, pos - 120)
        pre = text[start:pos]
        post = text[pos : pos + 300]
        tag: dict = {"ID": tag_id}

        dt = list(re.finditer(r'DataType="([A-Za-z]+)"', pre))
        if dt:
            tag["DataType"] = dt[-1].group(1)

        nm = list(re.finditer(r'Name="([^"]+)"', text[start : pos + 5]))
        if nm:
            raw = nm[-1].group(1)
            clean = re.split(r"\?{2,}", raw)[0].strip("?")
            if clean and clean != "?":
                normalized = _normalize_name(clean)
                if normalized in seen_name:
                    continue
                seen_name.add(normalized)
                tag["Name"] = normalized
        elif tag_id.startswith("?"):
            continue

        bo = re.search(r'yteOffset="?([0-9]+)"', post)
        if bo:
            tag["ByteOffset"] = bo.group(1)

        post_la = post[: bo.start()] if bo else post
        la = re.search(r'LogicalAddress="(%[^"]{1,12})"', post_la)
        if la:
            raw_la = la.group(1)
            if area_prefix and not raw_la.startswith(area_prefix):
                garbled = re.match(r"%I43\.([0-7])", raw_la)
                if garbled:
                    tag["_garbled_bit"] = garbled.group(1)
            elif not re.search(r"\?{3,}", raw_la):
                tag["LogicalAddress"] = raw_la.rstrip("?")

        if "_garbled_bit" in tag:
            bit = tag.pop("_garbled_bit")
            if "ByteOffset" in tag:
                area_letter = area_prefix[1]
                tag["LogicalAddress"] = f"%{area_letter}{tag['ByteOffset']}.{bit}"

        if "LogicalAddress" not in tag and "ByteOffset" in tag:
            if area_prefix in ("%I", "%Q"):
                area_letter = area_prefix[1]
                tag["LogicalAddress"] = f"%{area_letter}B{tag['ByteOffset']}"

        la_val = tag.get("LogicalAddress", "")
        if la_val and "ByteOffset" in tag and re.match(r"^%[A-Z]{2,}$", la_val):
            tag["LogicalAddress"] = f"{la_val}{tag['ByteOffset']}"

        tags.append(tag)

    return tags


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main():
    areas_requested = [a.upper() for a in sys.argv[1:] if a.upper() in AREAS]
    if not areas_requested:
        areas_requested = list(AREAS)

    fdict = _build_fdict()
    non_zero = sum(1 for b in fdict if b)
    print(f"PLC: {PLC_HOST}:{PLC_PORT}")
    print(f"FDICT: {non_zero} positions mapped of 32768 (Adler-32: 0xce9b821b)\n")

    total = 0
    for area in areas_requested:
        rid = AREAS[area]
        print(f">> Area {area}  (RID={rid}) ... ", end="", flush=True)

        data = _fetch_area(rid, fdict)
        if data is None:
            print("ERROR: compressed blob not found or decompression failed")
            continue

        tags = _extract_tags(data, area_prefix="%" + area)
        total += len(tags)
        print(f"{len(tags)} tags found")

        if tags:
            print(f"  {'Name':<22} {'Type':<8} {'Address':<18} {'Offset':<8} ID")
            print(f"  {'-' * 22} {'-' * 8} {'-' * 18} {'-' * 8} --")
            for t in tags:
                name = t.get("Name", "?")
                dtype = t.get("DataType", "?")
                addr = t.get("LogicalAddress", "?")
                offset = t.get("ByteOffset", "?")
                tid = t["ID"]
                print(f"  {name:<22} {dtype:<8} {addr:<18} {offset:<8} {tid}")
        print()

    print(f"Total: {total} tags")
    print()
    print('Note: 6 M-area tags (Byte/Word type) show LogicalAddress="?" —')
    print("structural limit of the S7CommPlus EXPLORE protocol (see module docstring).")


if __name__ == "__main__":
    main()
