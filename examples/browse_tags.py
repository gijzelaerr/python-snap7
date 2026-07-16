"""browse_tags.py — Read symbolic I/Q/M tags from an S7-1200 PLC (V3 protocol).

PROOF OF CONCEPT — not a supported library feature.

Technique: EXPLORE + zlib decompression with a partial preset dictionary
(FDICT, Adler-32 0xce9b821b) reconstructed via "oracle" analysis. The same
FDICT is used for all three areas (I, Q, M) and is shared by S7-1200 FW V4.5
("G1") and FW V4.1 ("G2"), confirmed on independent Wireshark pcapng captures.

Results on S7-1200 CPU 1212C DC/DC/DC, FW V4.5 (40-tag reference project):
  I area (RID=80): 13/13 complete
  Q area (RID=81): 11/11 complete
  M area (RID=82): Byte/Word/DWord type resolved via symbolic READ (see below)

M area Byte/Word/DWord — resolved via a symbolic READ:
  The EXPLORE blob does NOT carry the SIMATIC data type of an M tag: the
  DataType attribute decodes to a constant (a back-reference to the same
  preset-dict position for a Byte, a Word and a DWord tag alike — verified
  with an oracle on tags of known type). So %MB / %MW / %MD cannot be told
  apart from the blob; those tags only expose a correct ByteOffset.

  A symbolic READ recovers it: reading a tag by its LID returns the value as
  a fixed-width raw block whose width IS the declared type size — 1 byte for
  %MB, 2 for %MW, 4 for %MD. _refine_m_widths() does this for every non-Bool
  M tag (Bool tags are already bit-addressed by EXPLORE). The XML ID attribute
  equals the read LID. Verified live on an S7-1200 FW V4.1 with controlled
  tags: Byte=0x12→1B, Word=0x1234→2B, DWord=0x12345678→4B (values exact).

  Safety: if the ID has any unmapped digit ('?') the LID is uncertain and the
  refinement is skipped — better a '?' than a confident wrong type.

The FDICT is firmware-family specific. On a PLC whose tags reference
unmapped dictionary positions, some fields decode to '?'.

Usage:
    python browse_tags.py 192.168.5.11                 # all areas, plaintext
    python browse_tags.py 192.168.5.11 --tls           # G2 (TLS required)
    python browse_tags.py 192.168.5.11 I Q             # only I and Q areas
    python browse_tags.py 10.0.0.5 --tls --password s3cret M

Requires the python-snap7 S7CommPlus support (_build_explore_payload_v3,
collect_explore_frames) to be available in the installed `s7` package.
"""

import argparse
import re
import zlib

from s7commplus.client import _build_explore_payload_v3, _build_symbolic_read_payload
from s7commplus.connection import S7CommPlusConnection
from s7commplus.protocol import FunctionCode

AREAS = {"I": 80, "Q": 81, "M": 82}


# ── Partial preset dictionary (647 of 32768 positions mapped) ────────────────


def _build_fdict() -> bytes:
    d = bytearray(32768)

    def s(p, t):
        for i, c in enumerate(t.encode("latin-1")):
            d[p + i] = c

    # Leading block of a Word element (Tag_04, %IW43, ID=9) — I area
    s(0x7DB3, 'Tags Name="Tag_04" DataType="Word" ')
    # First Q-area element (ID=9): oracle Q pos 55-89 RUN[35] dict[7c3f..7c61]
    # Evidence: literal '2' at pos 183 = bit offset → %Q0.2 = Tag_2
    # Byte count: 'Tags Name="Tag_02" DataType="Bool" ' = 35c ✓
    s(0x7C3F, 'Tags Name="Tag_02" DataType="Bool" ')
    # ID attribute
    s(0x7B9C, 'ID="')
    s(0x7BA0, '9" HmiVisible="')
    # Boolean values
    s(0x7FC5, "True")
    s(0x7FE7, 'Visible="')
    s(0x7F36, 'True"')
    # Common attribute block
    s(0x7F71, '" HmiAccessible="True" Retain="False" Logical')
    s(0x7FA0, 'Address="%IW"')
    d[0x7FAC] = ord('"')
    s(0x7FAD, ' ByteOffset="')
    # Element separator: closes the current element, opens the next
    s(0x7CC3, '" />')
    d[0x7CC7] = ord("<")
    s(0x7CC8, "Tags")
    d[0x7CCC] = ord(" ")
    # Misc
    s(0x7CC0, '="1')
    s(0x7C0A, '0" ')
    d[0x7CEA] = ord(" ")
    d[0x7C14] = ord(" ")
    # Separator: '/><Tags' (7c0d..7c13) + 'HmiVisible=' (7c15..7c1f)
    # Confirmed by oracle Q/M: RUN[36] dict[7bfc..7c1f] and RUN[22] dict[7c0a..7c1f]
    s(0x7C0D, "/><Tags")  # 7c0d..7c13
    s(0x7C15, "HmiVisible=")  # 7c15..7c1f
    # Bool tag names (Tag_0XX scheme)
    d[0x7F3B] = ord(" ")  # space before Name=
    s(0x7F3C, 'Name="Tag_0')  # 7f3c..7f46
    d[0x7F46] = ord("6")
    s(0x7F47, '" DataType="Bool" ')
    # Root element
    s(0x7FF1, "ControllerTags>")
    # 88-char block for a Bool tag (split around the 0x7ed6-0x7ed7 gap)
    b88 = b'" Comment="" HmiVisible="True" HmiAccessible="True" Retain="False" LogicalAddress="%I43.'
    for i in range(63):
        d[0x7E97 + i] = b88[i]
    for i in range(25):
        d[0x7ED8 + i] = b88[63 + i]
    # Close LogicalAddress + open ByteOffset attr (14c)
    # Oracle M: after literal bit-digit, RUN[14] dict[7ef2..7eff] = '" ByteOffset="'
    s(0x7EF2, '" ByteOffset="')  # 7ef2..7eff

    # Q/M Name opener: Visible="True" Name=" prefix + Tag_1 prefix
    # Confirmed by oracle M: RUN[12] dict[7b79..7b84] precedes Clock_X names
    s(0x7B79, 'True" Name="Tag_1')  # 7b79..7b89
    # Bool DataType+ID block for M-area tags
    # Confirmed by oracle M: RUN[22] dict[7b8a..7b9f] after Clock_X names
    s(0x7B8A, '" DataType="Bool" ID="')  # 7b8a..7b9f
    # "output" suffix in Q-area names (0_output, 100_output, output_0_0)
    # Confirmed by oracle Q: RUN[7] dict[7f17..7f1d] after literal 'o'
    s(0x7F17, 'utput" ')  # 7f17..7f1d
    # G2 FW V4.1: 'nput' for I-area tag 'input_1' (i=literal, nput=FDICT[7e50..7e53])
    # Confirmed by oracle G2 I area: RUN[4] dict[7e50..7e53] after literal 'i'
    s(0x7E50, "nput")  # 7e50..7e53
    # G2 FW V4.1: Q-area LogicalAddress block (25c) = same as dict[7ed8..7ef0]
    # Confirmed by oracle G2 Q area: RUN[25] dict[7be2..7bfa] → garbled '%I43.1' → %Q0.1
    s(0x7BE2, 'se" LogicalAddress="%I43.')  # 7be2..7bfa
    # "Tag_" prefix for M-area names (Tag_11, Tag_5, Tag_20, ...)
    # Confirmed by oracle M: dict[7e7a..7e7d] precedes the name digit
    s(0x7E7A, "Tag_")  # 7e7a..7e7d
    # Digit '5' + name close for tags whose second digit is 5 (Tag_5/15/25)
    # DataType not set here: same block serves Bool and Word
    d[0x7E7E] = ord("5")  # name digit
    d[0x7E7F] = ord('"')  # closes Name="
    # Digit '3' + name close + DataType for tags with digit 3 (Tag_3, Tag_13)
    # Oracle Q: dict[7d08..7d1a] (19c) used twice (Tag_13 ID=13, Tag_3 ID=25)
    d[0x7D08] = ord("3")  # name digit
    d[0x7D09] = ord('"')  # closes Name="
    s(0x7D0A, ' DataType="Bool" ')  # 7d0a..7d1a

    # M-area Tag_1 megablock: chars 54..102 (dict[7baf..7bdf]) = 49c
    # = 'True" HmiAccessible="True" Retain="False" Logical'
    # Also used by Q-area tags via dict[7ba1..7bdf] (63c) for the HmiVisible suffix
    s(0x7BAF, 'True" HmiAccessible="True" Retain="False" Logical')  # 7baf..7bdf

    # First digit of the 2-digit IDs of the M-area Clock tags (ID=1X)
    # Clock_2.5Hz→"13", Clock_2Hz→"14", Clock_1Hz→"16", Clock_0.625Hz→"17", ...
    d[0x7C66] = ord("1")
    # Second digit of Clock_1.25Hz ID: oracle M pos 893 → dict[7e96..7ed5] RUN[64]
    # The '5' is NOT literal (unlike '6' for Clock_1Hz) → comes from the FDICT
    d[0x7E96] = ord("5")

    # Middle of the Q/M element separator: HmiVisible=" (12c)
    # Q oracle: RUN[22] dict[7cc3..7cd8] = '" /><Tags HmiVisible="' (22c)
    s(0x7CCD, 'HmiVisible="')  # 7ccd..7cd8

    # Second digit of a 2-digit ID: pattern 7c66='1', literal, 7c68..7c75
    # Oracle M: Clock_5Hz uses RUN[16] dict[7c66..7c75] = '1' + dict[7c67] + '" HmiVisible="'
    # dict[7c67]='2': Clock_5Hz→ID=12, Tag_18(M)→ID=22 (completes seq 20-25)
    d[0x7C67] = ord("2")
    # Close ID + open HmiVisible attr (14c): confirmed by Clock_2.5Hz/2Hz
    s(0x7C68, '" HmiVisible="')  # 7c68..7c75
    # Rest of the 62c chain: True" HmiAccessible="True" Retain="False" Logica (48c)
    # NOTE: exactly 48c — ends at 'Logica' (the trailing 'l' is NOT included);
    # that 'l' is the first char of the next block dict[7d62]
    s(0x7C76, 'True" HmiAccessible="True" Retain="False" Logica')  # 7c76..7ca5

    # Q-area Int/Word LogicalAddress: 'l' + Address="%QW" ByteOffset=2 (27c)
    # Oracle Q pos 352-378: RUN[27] dict[7d62..7d7c]
    # TIA truth: Tag_13=%QW200, Tag_14=%QW205, Tag_15=%QW25 — all ByteOffset start with '2'
    s(0x7D62, 'lAddress="%QW" ByteOffset=2')  # 7d62..7d7c

    # DataType="Bool" for tags whose second digit is '5': oracle Q Tag_15 uses dict[7e7e..7e90]
    # Shared with M-area Tag_5 (same 17c block) and Q-area Tag_25 (uses 7e7e..7e90)
    s(0x7E80, ' DataType="Bool" ')  # 7e80..7e90

    # NOTE: dict[7dc3..7dd5] = '4" DataType="Word" ' (already covered by the 7db3 line, 35c)
    # Q oracle Tag_14 and Tag_24 reuse this block → DataType="Word" (not "Bool"). Do not overwrite.

    # Close LogicalAddress bit + open ByteOffset attr (14c)
    # Oracle Q Tag_2: RUN[36] dict[7bfc..7c1f] after literal '2' → 14c + dict[7c0a]='0' → ByteOffset="0"
    # Oracle M Clock_2.5Hz: same → ByteOffset="0"
    # Oracle Q Tag_25: RUN[15] dict[7bfb..7c09] → ByteOffset="500"
    s(0x7BFC, '" ByteOffset="')  # 7bfc..7c09

    # LogicalAddress bit digit: Clock_5Hz → %M0.1; same byte serves Tag_25 Q → %Q500.1
    d[0x7BFB] = ord("1")

    # Bit digit Clock_1.25Hz → %M0.4 (in the 40c run dict[7ed8..7eff], 7ef1 is the gap)
    d[0x7EF1] = ord("4")

    # ByteOffset digit/closure for M-area tags (from oracle_M):
    # dict[7f00]='4': 3rd digit of ByteOffset=234 (Tag_11 %MB234)
    # dict[7f01]='"': ByteOffset close for Tag_11/16/18
    # dict[7e37]='3': 2nd digit of 43 (Tag_5 %MW43) and 53 (Tag_20 %MW53)
    # dict[7e38]='"': ByteOffset close for Tag_5 and Tag_20
    d[0x7F00] = ord("4")
    d[0x7F01] = ord('"')
    d[0x7E37] = ord("3")
    d[0x7E38] = ord('"')

    # ID second-digit + closing quote for two-digit M-tag IDs (oracle back-refs
    # dict[7d20..21]='3"' and dict[7ddb..dc]='4"'). Needed so IDs like 13/14 read
    # cleanly, which _refine_m_widths() then uses as the LID. Positions were 0.
    d[0x7D20] = ord("3")
    d[0x7D21] = ord('"')
    d[0x7DDB] = ord("4")
    d[0x7DDC] = ord('"')

    return bytes(d)


# ── Connection and decompression ────────────────────────────────────────────


def _connect(host: str, port: int, use_tls: bool, password: str) -> S7CommPlusConnection:
    """Open a fresh connection. The PLC resets the TCP session after the first
    symbolic EXPLORE/READ, so one connection is used per operation.

    No unittest.mock is needed: connect() already wraps the optional post-auth
    legitimation in a try/except and only logs a warning if it is skipped
    (e.g. no-password PLCs, or the plaintext V3 path where legitimation needs TLS).
    """
    conn = S7CommPlusConnection(host=host, port=port)
    conn.connect(use_tls=use_tls, password=password, timeout=8.0)
    return conn


def _fetch_area(rid: int, fdict: bytes, host: str, port: int, use_tls: bool, password: str) -> bytes | None:
    """Connect to the PLC, send EXPLORE for the given RID, decompress the blob."""
    conn = _connect(host, port, use_tls, password)
    try:
        resp = conn.send_request(FunctionCode.EXPLORE, _build_explore_payload_v3(rid))
        full = conn._collect_explore_frames(resp)
    finally:
        try:
            conn.disconnect()
        except Exception:
            pass

    # Find the preset-dictionary blob (magic 78 7D)
    p = full.find(b"\x78\x7d")
    if p < 0:
        return None
    raw_deflate = full[p + 6 :]  # skip 2 magic bytes + 4 dict Adler-32 bytes
    try:
        return zlib.decompressobj(wbits=-15, zdict=fdict).decompress(raw_deflate)
    except zlib.error:
        return None


# ── Tag extraction ──────────────────────────────────────────────────────────


def _normalize_name(raw: str) -> str:
    """Normalize internal PLC tag names to the TIA Portal form.

    S7-1200 FW V4.5 stores names internally as 'Tag_04', 'Tag_06' (leading
    zero), while TIA Portal exports 'Tag_4', 'Tag_6'. Strip the leading zero.
    """
    m = re.match(r"^(Tag_)0+([0-9]+)$", raw)
    if m:
        return m.group(1) + m.group(2)
    return raw


def _extract_tags(data: bytes, area_prefix: str = "") -> list[dict]:
    """Extract tags from the decompressed XML blob.

    ID values are always literal bytes in the deflate stream (always visible).
    Anchor on each ID="N" and look for Name/DataType in the window before it.
    Null bytes (unknown dict positions) become '?' in the text.
    """
    text = data.replace(b"\x00", b"?").decode("latin-1")
    tags: list[dict] = []
    seen_id: set[str] = set()
    seen_name: set[str] = set()
    _synthetic = 0

    # Some IDs sit in unknown dict positions (null→'?'). Capture up to 6 chars
    # after ID=" including a possible '?' terminator.
    for m in re.finditer(r'ID="([0-9?]{1,6})[?"]', text):
        raw_id = m.group(1)
        # Keep only the leading digits (stop at the first '?')
        leading = re.match(r"^([0-9]+)", raw_id)
        # Uncertain ID: a '?' after the leading digits means one or more digits
        # fell in an unmapped FDICT position, so the number read is partial and
        # NOT safe to use as a LID (a READ would hit the wrong object).
        id_uncertain = "?" in raw_id
        if leading:
            tag_id = leading.group(1)
            if tag_id in seen_id:
                continue
            seen_id.add(tag_id)
            display_id = tag_id
        else:
            # ID entirely in FDICT (all '?') → synthetic key
            tag_id = f"?{_synthetic}"
            _synthetic += 1
            display_id = "?"

        pos = m.start()

        # Use the last <Tags or Visible=" as the element start boundary
        anchors = [a.start() for a in re.finditer(r'<Tags|Visible="', text[:pos])]
        start = anchors[-1] if anchors else max(0, pos - 120)

        pre = text[start:pos]
        name_ctx = text[start : min(len(text), pos + 5)]
        post = text[pos : min(len(text), pos + 300)]

        tag: dict = {"ID": display_id}
        if id_uncertain:
            tag["_id_uncertain"] = True

        # DataType: always before the ID (pre-window only)
        dt = list(re.finditer(r'DataType="([A-Za-z]+)"', pre))
        if dt:
            tag["DataType"] = dt[-1].group(1)

        # Name: extend 5 chars past the ID start to catch a null-encoded '"'
        nm = list(re.finditer(r'Name="([^"]+)"', name_ctx))
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
            continue  # ID and name both unknown: drop

        # Restrict the ByteOffset search to the CURRENT element (stop at the next
        # tag's 'Name="'). Without this, the 300-char window bleeds into the next
        # tag and the fallbacks below can latch onto its (possibly truncated) offset.
        _nxt = post.find('Name="', 6)
        elem = post[:_nxt] if _nxt > 0 else post

        # Find ByteOffset first. Anchor on 'yteOffset=' to handle M-area gap tags
        # where 'B' is in an unknown FDICT position (null → 'yteOffset=').
        bo = re.search(r'yteOffset="?([0-9]+)"', elem)
        if not bo:
            # Fallback 1: if the 'ByteOffset=' label is unmapped, the numeric value
            # still survives as a literal right before the element close: ="100" />.
            bo = re.search(r'="([0-9]+)"\s*/>', elem)
        if not bo:
            # Fallback 2: the element close itself may be garbled (="104<nulls>).
            # ByteOffset always follows LogicalAddress in the XML, so anchor after
            # the last 'Logical' marker and take the first ="N. The ID (also ="N)
            # sits before 'Logical'; the LogicalAddress value starts with '%'.
            tail = elem[elem.rfind("Logical") :] if "Logical" in elem else ""
            bo = re.search(r'="([0-9]{1,5})', tail) if tail else None
        if bo:
            tag["ByteOffset"] = bo.group(1)

        # LogicalAddress: search within the current element only. 'elem' already
        # stops at the next tag, so the next element's %I43.X address cannot leak
        # in; there is exactly one LogicalAddress per element (before ByteOffset).
        la = re.search(r'LogicalAddress="(%[^"]{1,12})"', elem)
        if la:
            raw_la = la.group(1)
            if area_prefix and not raw_la.startswith(area_prefix):
                if area_prefix in ("%Q", "%M"):
                    garbled = re.match(r"%I43\.([0-7])", raw_la)
                    if garbled:
                        tag["_garbled_bit"] = garbled.group(1)
            elif not re.search(r"\?{3,}", raw_la):
                # I area: the '43' in '%I43.x' comes from the FDICT sample dict,
                # NOT the real tag (same source as the %Q/%M garbled path). Only the
                # bit digit is a real literal. If ByteOffset disagrees, rebuild
                # %I{ByteOffset}.{bit}. Fixes G2 input_1: %I43.0 → %I0.0.
                mi = re.match(r"%I43\.([0-7])$", raw_la)
                if area_prefix == "%I" and mi and tag.get("ByteOffset") not in (None, "43"):
                    tag["_garbled_bit"] = mi.group(1)
                else:
                    tag["LogicalAddress"] = raw_la.rstrip("?")

        if "_garbled_bit" in tag:
            bit = tag.pop("_garbled_bit")
            if "ByteOffset" in tag:
                # The bit digit in the garbled %I43.X address is always literal and
                # correct — always use the bit form %{area}{bo}.{bit}.
                area_letter = area_prefix[1]
                tag["LogicalAddress"] = f"%{area_letter}{tag['ByteOffset']}.{bit}"

        # Byte-type fallback for I/Q: Bool tags trigger _garbled_bit above,
        # Word/Int tags have %IW/%QW visible. The only remaining case is Byte
        # (%IB / %QB): oracle analysis proved the value is not encoded. Rebuild it.
        if "LogicalAddress" not in tag and "ByteOffset" in tag:
            if area_prefix in ("%I", "%Q"):
                area_letter = area_prefix[1]
                tag["LogicalAddress"] = f"%{area_letter}B{tag['ByteOffset']}"

        # Reconstruct %IW/%QW/%MW → %IW{N} etc. using ByteOffset.
        la_val = tag.get("LogicalAddress", "")
        if la_val and "ByteOffset" in tag and re.match(r"^%[A-Z]{2,}$", la_val):
            tag["LogicalAddress"] = f"{la_val}{tag['ByteOffset']}"

        tags.append(tag)

    return tags


# ── M-area type resolution via symbolic READ (route B) ───────────────────────
#
# The EXPLORE blob cannot carry the SIMATIC type of an M tag (the DataType
# attribute is a constant back-reference in the compressed stream — identical for
# a Byte, a Word and a DWord tag). A symbolic READ recovers it: the PLC returns
# the value as a fixed-width raw block whose width equals the declared type size.

_READ_TRAILER = bytes.fromhex("000400000000")  # fixed GetMultiVariables trailer
_WIDTH_TYPE = {1: ("%MB", "Byte"), 2: ("%MW", "Word"), 4: ("%MD", "DWord")}


def _read_symbolic_width(lid: int, host: str, port: int, use_tls: bool, password: str) -> int | None:
    """Symbolic READ of an M tag by LID → value width in bytes = type size.

    The response is  <value bytes, fixed width> 0x00 + trailer(00 04 00 00 00 00).
    width = len(response) - len(trailer) - 1(pad).  None if the read fails.
    """
    try:
        conn = _connect(host, port, use_tls, password)
    except Exception:
        return None
    try:
        payload = _build_symbolic_read_payload(access_area=AREAS["M"], lids=[lid])
        resp = conn.send_request(FunctionCode.GET_MULTI_VARIABLES, payload)
    except Exception:
        return None
    finally:
        try:
            conn.disconnect()
        except Exception:
            pass
    if not resp.endswith(_READ_TRAILER):
        return None
    body = resp[: -len(_READ_TRAILER)]
    if len(body) < 2:  # need at least value(>=1) + pad(1)
        return None
    return len(body) - 1


def _refine_m_widths(tags: list[dict], host: str, port: int, use_tls: bool, password: str) -> None:
    """Resolve %MB/%MW/%MD for non-Bool M tags from the width of a symbolic READ.

    Bool tags are bit-addressed (%M<byte>.<bit>) and already correct from EXPLORE.
    For the rest, the XML ID attribute is the read LID. Skips tags with an
    uncertain ID so a wrong LID can never produce a confident wrong type.
    """
    for t in tags:
        if re.match(r"%M\d+\.\d", t.get("LogicalAddress", "")):
            continue  # Bool, bit-addressed: already resolved
        if t.get("_id_uncertain"):
            continue  # partial LID → a READ would hit the wrong object
        bo = t.get("ByteOffset")
        tid = t.get("ID", "")
        if bo is None or not tid.isdigit():
            continue
        width = _read_symbolic_width(int(tid), host, port, use_tls, password)
        mapping = _WIDTH_TYPE.get(width)
        if mapping:
            prefix, dtype = mapping
            t["LogicalAddress"] = f"{prefix}{bo}"
            t["DataType"] = dtype
            t["_type_source"] = "read"


# ── Main ─────────────────────────────────────────────────────────────────────


def main():
    parser = argparse.ArgumentParser(
        description="Read symbolic I/Q/M tags from an S7-1200 PLC (V3 protocol).",
    )
    parser.add_argument("host", help="PLC IP address or hostname")
    parser.add_argument(
        "areas",
        nargs="*",
        default=None,
        help="Areas to browse: I, Q and/or M (default: all)",
    )
    parser.add_argument("--port", type=int, default=102, help="TCP port (default: 102)")
    parser.add_argument(
        "--tls",
        action="store_true",
        help="Activate TLS (required on PLCs that enforce secure PG/PC comms, e.g. G2 FW V4.1)",
    )
    parser.add_argument("--password", default="", help="PLC password (default: none)")
    args = parser.parse_args()

    requested = [a.upper() for a in args.areas if a.upper() in AREAS] if args.areas else list(AREAS)
    if not requested:
        requested = list(AREAS)

    fdict = _build_fdict()
    print(f"PLC: {args.host}:{args.port} (tls={args.tls})")
    print(f"Partial FDICT: {sum(1 for b in fdict if b)} of 32768 positions known\n")

    total = 0
    for area in requested:
        rid = AREAS[area]
        print(f">> Area {area}  (RID={rid}) ... ", end="", flush=True)

        try:
            data = _fetch_area(rid, fdict, args.host, args.port, args.tls, args.password)
        except Exception as exc:
            print(f"CONNECTION ERROR: {exc!r}")
            continue
        if data is None:
            print("ERROR: no compressed blob found")
            continue

        tags = _extract_tags(data, area_prefix="%" + area)
        if area == "M":
            # Route B: resolve %MB/%MW/%MD of non-Bool M tags via a symbolic READ
            _refine_m_widths(tags, args.host, args.port, args.tls, args.password)
        total += len(tags)
        print(f"{len(tags)} tags found")

        if tags:
            print(f"  {'Name':<22} {'Type':<8} {'Address':<18} {'Offset':<8} ID")
            print(f"  {'-' * 22} {'-' * 8} {'-' * 18} {'-' * 8} --")
            for t in tags:
                name = t.get("Name", "?")
                dtype = t.get("DataType", "?")
                if t.get("_type_source") == "read":
                    dtype += "*"  # type/address recovered via a symbolic READ
                addr = t.get("LogicalAddress", "?")
                offset = t.get("ByteOffset", "?")
                print(f"  {name:<22} {dtype:<8} {addr:<18} {offset:<8} {t['ID']}")
        if any(t.get("_type_source") == "read" for t in tags):
            print("  (* %MB/%MW/%MD type/address recovered via a symbolic READ by LID)")
        print()

    print(f"Total: {total} tags")


if __name__ == "__main__":
    main()
