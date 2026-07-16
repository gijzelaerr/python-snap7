"""Auto-generated from /tmp/HarpoS7/HarpoS7.Family0/Monoliths/Monolith3.cs.

DO NOT EDIT — regenerate via tools/transpile_harpo_monolith.py.

Mechanically transpiled from HarpoS7's Family-0 ``Monolith3.Execute``.
Vector-verified against ``HarpoS7.Family0.Tests/Blobs/Monoliths/``.
"""

from __future__ import annotations

import struct

_U32 = 0xFFFFFFFF


def _shr(x: int, n: int) -> int:
    """Logical right-shift (mask to uint32 before shifting).

    Python's ``>>`` on negative ints does arithmetic shift (sign-extends).
    C#'s ``uint >> n`` does logical shift (zero-fills). This helper
    ensures Python behaves identically to C#.
    """
    return (x & _U32) >> n


def _to_uints(buf: bytes | bytearray) -> list[int]:
    n = len(buf) // 4
    return list(struct.unpack(f"<{n}I", bytes(buf[: n * 4])))


def _from_uints(uints: list[int]) -> bytes:
    return struct.pack(f"<{len(uints)}I", *(u & _U32 for u in uints))


def execute(destination: bytearray, source: bytes) -> None:
    """Run the transpiled body."""
    src_dwords = _to_uints(source)
    dst_dwords = _to_uints(destination)

    uVar24 = (src_dwords[0x1D]) & 0xFFFFFFFF
    uVar21 = (src_dwords[0x1C]) & 0xFFFFFFFF
    uVar86 = (src_dwords[0x24]) & 0xFFFFFFFF
    uVar36 = (src_dwords[0x1B]) & 0xFFFFFFFF
    uVar23 = (src_dwords[0x27]) & 0xFFFFFFFF
    uVar87 = (src_dwords[2]) & 0xFFFFFFFF
    uVar42 = (
        ((uVar24 & 0xEF9FD0FB ^ uVar21 ^ 0x50050151) & uVar36 ^ uVar24 & 0xC5F7FE05 ^ 0xE716DB50) & 0xFAEDAFFF
        ^ (uVar24 & 0xF865AFCF ^ 0x82088A74) & uVar21
    ) & 0xFFFFFFFF
    uVar65 = (
        (
            (
                (~(uVar23 & 0xFAEDBFFF) ^ uVar87 & 0xFAEDBFFF) & src_dwords[1] & 0xFDDF4FF6
                ^ (uVar23 & 0xDAECAAAF ^ 0xA44270FA) & uVar87
                ^ ~(uVar23 & 0xFEEFAFFF) & 0xA15070FA
            )
            & src_dwords[0]
            ^ ((uVar23 & 0xFAE5A7DB ^ 0x33F8DCE7) & uVar87 ^ ~(uVar23 & 0xFFFFBFFF) & 0x32E8CCE7) & src_dwords[1]
            ^ (uVar23 & 0x9281A508 ^ 0x7422053E) & uVar87
            ^ ~(uVar23 & 0xFEEDFFFF) & 0x7132053E
        )
        & src_dwords[0x24]
        ^ ~uVar87 & uVar42 & uVar23
    ) & 0xFFFFFFFF
    uVar84 = (src_dwords[0x10]) & 0xFFFFFFFF
    uVar85 = (src_dwords[0x11]) & 0xFFFFFFFF
    uVar61 = (src_dwords[9]) & 0xFFFFFFFF
    uVar19 = (src_dwords[0xB]) & 0xFFFFFFFF
    uVar38 = (src_dwords[0x29]) & 0xFFFFFFFF
    uVar20 = (src_dwords[10]) & 0xFFFFFFFF
    uVar1 = (uVar61 & 0x7AEDAF7A) & 0xFFFFFFFF
    uVar2 = (uVar61 & 0x6F9FD07A ^ 0x44E7EE00) & 0xFFFFFFFF
    uVar66 = (uVar19 & uVar2) & 0xFFFFFFFF
    uVar43 = ((uVar19 & 0x7D77FF4A ^ uVar1 ^ 0x61ADA70) & uVar20) & 0xFFFFFFFF
    uVar3 = (uVar61 & 0x51050150) & 0xFFFFFFFF
    uVar51 = (src_dwords[0xF]) & 0xFFFFFFFF
    uVar26 = (
        (src_dwords[0x11] & 0x6EE7ED72 ^ 0xCB1828F5) & src_dwords[0x10] ^ src_dwords[0x11] & 0x5442B22A ^ 0x5162216
    ) & 0xFFFFFFFF
    uVar4 = ((uVar85 & 0xEEE7EDF7 ^ 0x4B1828F4) & uVar84) & 0xFFFFFFFF
    uVar44 = (
        (
            ((~(uVar85 & 0xFEE7FFFF) & uVar84 ^ uVar85 & 0xF4E7F7AB ^ 0x1102014) & uVar38 ^ uVar61 & 0xF5E7D75B ^ 0x90820A4)
            & 0x4B1828F4
            ^ (uVar19 & 0x491028C4 ^ uVar61 & 0x4A0828F4 ^ 0x2180874) & uVar20
            ^ (uVar61 & 0x4B1800F0 ^ 0x40002804) & uVar19
        )
        & uVar23
        ^ (
            (((uVar84 ^ 0xFFFFFF5F) & 0x91808E4 ^ uVar85 & 0x4B182870) & uVar38 ^ uVar3 ^ uVar66 ^ uVar43 ^ 0x6216DB50) & uVar23
            ^ uVar38 & uVar26
            ^ 0x7FFFFF7A
        )
        & uVar51
        ^ (uVar85 & 0xD442B2AB ^ uVar4 ^ 0x85162217) & uVar38
    ) & 0xFFFFFFFF
    uVar5 = ((uVar61 & 0x621E5030 ^ 0x40064004) & uVar24) & 0xFFFFFFFF
    uVar27 = ((uVar61 & 0x620C0134 ^ 0x21A5034) & uVar24) & 0xFFFFFFFF
    uVar45 = (uVar61 & 0x40040110 ^ 0x80024) & 0xFFFFFFFF
    uVar87 = (
        (
            (
                ((uVar24 ^ 0xFFFFFFFB) & uVar21 & 0x60165104 ^ uVar24 & 0xA0109A40 ^ 0x40040140) & uVar19
                ^ (uVar61 & 0x60040100 ^ uVar27 ^ 0x125000) & uVar21
                ^ (uVar61 & 0xA2088A60 ^ 0x82189A60) & uVar24
                ^ (uVar61 ^ 0x40) & 0x40040140
            )
            & uVar20
            ^ (
                ((uVar61 ^ 0xDFEFEFFF) & 0x60165000 ^ uVar5) & uVar21
                ^ (uVar61 & 0xA2189060 ^ 0x80008A00) & uVar24
                ^ (uVar61 ^ 0xFFFFFFBF) & 0x40040040
            )
            & uVar19
            ^ (uVar21 & uVar45 ^ uVar61 & 0x40 ^ 0x80020) & uVar24
            ^ ~(~(uVar21 & 0xFFFFFFBF) & uVar61 & 0x40040140) & 0xE016DB40
        )
        & uVar36
        ^ (
            ((uVar21 & 0x2080030 ^ 0x80088A20) & ~uVar61 ^ uVar19 & 0x80008A00) & uVar20
            ^ ((uVar21 & 0x2080030 ^ 0x80088020) & uVar61 ^ 0x80008A00) & uVar19
            ^ (uVar61 & 0x10 ^ 0x80020) & uVar21
            ^ 0x82008A54
        )
        & uVar24
    ) & 0xFFFFFFFF
    uVar6 = (((uVar61 & 0xEAE5ADF7 ^ 0x8602C874) & uVar85 ^ uVar61 & 0x4A0828F4 ^ 0x2180874) & uVar84) & 0xFFFFFFFF
    uVar28 = ((uVar85 & 0xEC67EDC7 ^ 0x491028C4) & uVar84 ^ uVar85 & 0xD442B28B ^ 0x85162207) & 0xFFFFFFFF
    uVar7 = ((uVar61 & 0xD040A2AB ^ 0x84029220) & uVar85) & 0xFFFFFFFF
    uVar29 = (
        ((uVar61 & 0xEE87C0F3 ^ 0xC4E7EC05) & uVar85 ^ uVar61 & 0x4B1800F0 ^ 0x40002804) & uVar84
        ^ (uVar61 & 0xC40290AB ^ 0xC442A201) & uVar85
        ^ uVar61 & 0x85160013
        ^ 0x84062205
    ) & 0xFFFFFFFF
    uVar30 = (((uVar61 & 0x40050151 ^ 0xA806E1A4) & uVar85 ^ uVar61 & 0x41000050 ^ 0x90820A4) & uVar84) & 0xFFFFFFFF
    uVar8 = ((uVar61 & 0x50000001 ^ 0x8002B2A0) & uVar85) & 0xFFFFFFFF
    uVar31 = (uVar61 & 0xA91810EB ^ 0x80000A05) & 0xFFFFFFFF
    uVar75 = (
        (
            (
                (
                    (
                        (uVar19 & 0xB9101ACF ^ uVar61 & 0xB8080AEF ^ 0x80181A64) & uVar20
                        ^ uVar19 & uVar31
                        ^ uVar61 & 0x11000041
                        ^ 0xA90812A4
                    )
                    & uVar23
                    ^ src_dwords[0x11] & 0x6EE7ED72
                    ^ 0x7200321A
                )
                & uVar84
                ^ (
                    (uVar19 & 0xD77DD46 ^ uVar61 & 0x8ED8D46 ^ 0x41AD844) & uVar20
                    ^ (uVar61 & 0xD9FD042 ^ 0x4E7CC04) & uVar19
                    ^ uVar61 & 0x1050140
                    ^ 0x90ED104
                )
                & uVar23
                ^ ((uVar3 ^ uVar66 ^ uVar43 ^ 0x290EF320) & uVar23 ^ 0x2BBD4D50) & uVar85
                ^ 0x8E9FF50
            )
            & uVar38
            ^ 0x7FFFFF7A
        )
        & uVar51
        ^ ~(
            (
                (
                    (uVar19 & uVar28 ^ uVar61 & 0x80042217 ^ uVar7 ^ uVar6 ^ 0x84120214) & uVar20
                    ^ uVar19 & uVar29
                    ^ uVar61 & 0x1040011
                    ^ uVar8
                    ^ uVar30
                    ^ 0x81062204
                )
                & uVar38
                ^ 0x4B1828F4
            )
            & uVar23
        )
    ) & 0xFFFFFFFF
    uVar41 = (src_dwords[2]) & 0xFFFFFFFF
    uVar63 = (src_dwords[0x14]) & 0xFFFFFFFF
    uVar71 = (src_dwords[0x13]) & 0xFFFFFFFF
    uVar52 = (src_dwords[0x12]) & 0xFFFFFFFF
    uVar43 = (src_dwords[1]) & 0xFFFFFFFF
    uVar66 = (src_dwords[2]) & 0xFFFFFFFF
    uVar40 = (src_dwords[0x14]) & 0xFFFFFFFF
    uVar32 = ((uVar24 ^ 0x869ADA74) & uVar21) & 0xFFFFFFFF
    uVar76 = (
        (
            (
                ((uVar41 & 0x9280A02A ^ 0xCC4E6AAE) & uVar63 ^ ~(uVar41 & 0xFFBFBF3F) & 0xA15060FA) & uVar43
                ^ ((uVar41 & 0xB1900032 ^ 0xED5E4AF6) & uVar43 ^ src_dwords[2] & 0xFDDE4AB6 ^ 0xA15040F2) & uVar71
                ^ (src_dwords[2] ^ 0xA15175FA) & src_dwords[0x14] & 0xDEEEFAAF
                ^ ~(src_dwords[2] & 0xFFFFFFBF) & 0xA15070FA
            )
            & src_dwords[0x12]
            ^ (
                ((uVar41 & 0xB390A01A ^ 0xE95462DA) & uVar63 ^ uVar41 & 0x32808022 ^ 0x204848E6) & uVar43
                ^ (uVar66 & 0xFBF4F29B ^ 0xA15070DA) & src_dwords[0x14]
                ^ uVar66 & 0x32E8C8A7
                ^ 0x204040E2
            )
            & src_dwords[0x13]
            ^ ((uVar41 & 0x9280A008 ^ 0x84022008) & uVar40 ^ uVar66 & 0x3110003A ^ 0x6112003E) & uVar43
            ^ (uVar66 ^ 0xE97D7FFF) & uVar40 & 0x9682A008
            ^ (uVar41 ^ 0x2110003A) & 0x7132003E
        )
        & src_dwords[0]
        ^ (
            ((uVar66 & 0xDAE4F2A3 ^ 0x106848AF) & uVar40 ^ uVar66 & 0xA04070E2 ^ 0x204040EA) & uVar43
            ^ ((uVar66 & 0xF8C547E2 ^ 0x30484DE6) & uVar43 ^ uVar66 & 0xB5930532 ^ 0x71120536) & uVar71
            ^ (uVar66 & 0x9682A02A ^ 0x5022002E) & uVar63
            ^ (uVar41 ^ 0x2110003A) & 0xA110203A
        )
        & uVar52
        ^ (
            ((uVar66 & 0xFAE5F7C3 ^ 0x306045CB) & uVar63 ^ uVar66 & 0x32E0C4E3 ^ 0x30684CE7) & uVar43
            ^ (uVar66 & 0xB391A51A ^ 0x7130051A) & uVar63
            ^ uVar66 & 0x32808422
            ^ 0x30200426
        )
        & uVar71
        ^ ((uVar66 & 0x9281A500 ^ 0x10000508) & uVar63 ^ uVar66 & 0x70200522 ^ 0xA2A1A026) & uVar43
        ^ ((uVar66 ^ 0x10020508) & uVar63 ^ uVar66 & 0x10020500) & 0x9683A508
        ^ 0x8ECDFAC1
    ) & 0xFFFFFFFF
    uVar55 = (src_dwords[0x1F]) & 0xFFFFFFFF
    uVar73 = (src_dwords[0x20]) & 0xFFFFFFFF
    uVar46 = (
        (
            (
                ((uVar24 & 0x60165104 ^ 0x9873FECF) & uVar21 ^ uVar24 & 0x4D074A8B ^ 0x11010001) & uVar36
                ^ (uVar24 & 0x44676405 ^ uVar32 ^ 0xE29EDB70) & 0xFD77FFCF
            )
            & uVar19
            ^ (
                (uVar61 & 0x9AE9AEFF ^ uVar27 ^ 0x821ADA74) & uVar21
                ^ (uVar61 & 0x48850A9B ^ 0x4024A10) & uVar24
                ^ (uVar61 ^ 0x10) & 0x10010011
            )
            & uVar36
            ^ ((uVar61 & 0xFA6DAFFF ^ 0x861ADA74) & uVar24 ^ ~(uVar61 & 0xFBEDAFFF) & 0x861ADA74) & uVar21
            ^ (uVar61 & 0x40ED2425 ^ 0x40A4024) & uVar24
            ^ uVar61 & 0xE2048B50
            ^ 0x8212DA50
        )
        & uVar20
        ^ (
            (
                (uVar61 & 0x8A9BD0FB ^ uVar5 ^ 0x80E3EE05) & uVar21
                ^ (uVar61 & 0x4D87409B ^ 0x44874A01) & uVar24
                ^ (uVar61 ^ 0x10001) & 0x1010011
            )
            & uVar36
            ^ ((uVar61 & 0xEF1FD0FB ^ 0xC467EE05) & uVar24 ^ uVar61 & 0x861AD070 ^ 0x8402CA04) & uVar21
            ^ (uVar61 & 0x448F4021 ^ 0x44E76405) & uVar24
            ^ uVar61 & 0xE216D050
            ^ 0xC006CA00
        )
        & uVar19
        ^ (
            (uVar24 & uVar45 ^ uVar61 & 0x10010051 ^ 0xE2048B50) & uVar21
            ^ (uVar61 & 0x41050011 ^ 0xE21ED070) & uVar24
            ^ uVar61 & 0x11010011
            ^ 0x40040150
        )
        & uVar36
        ^ ((uVar61 & 0x51050151 ^ 0xE01EDB60) & uVar24 ^ ~(uVar61 & 0x50) & 0x8212DA50) & uVar21
        ^ (uVar61 & 0x40050001 ^ 0xC00ECA20) & uVar24
        ^ ~(uVar61 & 0x40040150) & 0xE216DB50
    ) & 0xFFFFFFFF
    uVar92 = (src_dwords[0x1E]) & 0xFFFFFFFF
    uVar66 = (src_dwords[0xD]) & 0xFFFFFFFF
    uVar77 = ((uVar73 ^ 0xFFEFFF7F) & uVar55) & 0xFFFFFFFF
    uVar67 = (((uVar73 ^ 0x80) & 0xFF6FFFFF ^ uVar55) & uVar92) & 0xFFFFFFFF
    uVar9 = (src_dwords[0x20] & 0x940E181A) & 0xFFFFFFFF
    uVar27 = (uVar77 & 0xDFFFFFFF ^ uVar67) & 0xFFFFFFFF
    uVar59 = (~(src_dwords[0x20] & 0xFFEFFFFF)) & 0xFFFFFFFF
    uVar40 = (src_dwords[0xE]) & 0xFFFFFFFF
    uVar43 = (
        ~(
            (
                (
                    ((uVar9 ^ 0xB0001000) & src_dwords[0x1E] ^ (src_dwords[0x20] ^ 0xFFF9FFF3) & 0x9006100C) & src_dwords[0x1F]
                    ^ ((uVar27 ^ src_dwords[0x20] ^ 0x20800080) & uVar66 ^ 0x20000000) & 0xB0901080
                    ^ (src_dwords[0x1E] & 0x21060008 ^ 0x20000004) & src_dwords[0x20]
                )
                & src_dwords[0xC]
                ^ (
                    ((src_dwords[0x20] & 0x940A181A ^ 0x100080) & uVar55 ^ (uVar73 ^ 0x80) & 0x91021088) & uVar92
                    ^ (uVar55 & 0x12008C ^ 0x90101084) & uVar73
                    ^ 0x80
                )
                & uVar66
                ^ (((uVar59 & uVar92 ^ 0xFFEFFFFF) & 0xFFFFFFFB ^ uVar73) & uVar55 ^ uVar73 & 0x100004) & 0x90101004
                ^ 0xB0901080
            )
            & uVar40
        )
        ^ (
            (
                ((src_dwords[0x1F] ^ 0xFBF7F7ED) & src_dwords[0x1E] ^ src_dwords[0x1F] & 0x60008 ^ 0xFBF1F7E5)
                & uVar66
                & 0x940E181A
                ^ (src_dwords[0x1E] & 0x4080812 ^ 4) & src_dwords[0x1F]
                ^ 4
            )
            & src_dwords[0xC]
            ^ ((src_dwords[0x1F] & 0x940C1812 ^ 0x91041000) & uVar92 ^ src_dwords[0x1F] & 0x40000 ^ 0x90001000) & uVar66
            ^ 0x950E181E
        )
        & uVar73
    ) & 0xFFFFFFFF
    uVar25 = (src_dwords[0x17]) & 0xFFFFFFFF
    uVar64 = (src_dwords[0x15]) & 0xFFFFFFFF
    uVar74 = (src_dwords[0x25]) & 0xFFFFFFFF
    uVar37 = (src_dwords[0x28]) & 0xFFFFFFFF
    uVar33 = (
        (
            (uVar40 & 0xDB2EFFDF ^ uVar66 & 0x9A9FB9BB ^ 0x9E9F6) & src_dwords[0xC]
            ^ (uVar40 & 0xD9BB5EFF ^ 0xD3ADBF12) & uVar66
            ^ uVar40 & 0xD09012C4
            ^ 0x4AA0E7C1
        )
        & src_dwords[0x28]
    ) & 0xFFFFFFFF
    uVar47 = ((src_dwords[0x17] ^ 0x67413841) & 0xE7FF3947) & 0xFFFFFFFF
    uVar88 = (
        (
            (uVar66 & 0xBC9799BB ^ uVar40 & 0xBC66DF9F ^ 0x401C9B6) & src_dwords[0xC]
            ^ (uVar40 & 0x9CF35EBF ^ 0x94E59F12) & src_dwords[0xD]
            ^ uVar40 & 0xB0901284
            ^ 0xCA0C781
        )
        & src_dwords[0x28]
    ) & 0xFFFFFFFF
    uVar66 = (src_dwords[0xE]) & 0xFFFFFFFF
    uVar39 = (src_dwords[0x16]) & 0xFFFFFFFF
    uVar60 = (
        (
            (src_dwords[0xD] & 0x101C98AB ^ uVar66 & 0x110CDE8B ^ 0x8C8A2) & src_dwords[0xC]
            ^ (uVar66 & 0x11185EAB ^ 0x110C9E02) & src_dwords[0xD]
            ^ uVar66 & 0x10101280
            ^ 0xC681
        )
        & uVar37
    ) & 0xFFFFFFFF
    uVar66 = (src_dwords[0x17]) & 0xFFFFFFFF
    uVar66 = (
        ~(
            (
                (
                    (
                        (
                            (src_dwords[0x17] & 0xA69F3903 ^ 0xA49E813A) & src_dwords[0x15]
                            ^ src_dwords[0x17] & 0x9E823981
                            ^ 0xA41F9011
                        )
                        & src_dwords[0xD]
                        ^ ((src_dwords[0x17] & 0xE76E3947 ^ 0xA46EC11E) & uVar64 ^ src_dwords[0x17] & 0xDE223FC5 ^ 0xE44E9611)
                        & src_dwords[0xE]
                        ^ (uVar66 & 0x4092946 ^ 0x408C136) & uVar64
                        ^ uVar66 & 0x40029C4
                        ^ 0x4098010
                    )
                    & src_dwords[0xC]
                    ^ (
                        ((uVar66 & 0xC5FB1847 ^ 0x84FA403E) & uVar64 ^ uVar25 & 0xDCA21EC5 ^ 0xC45B1611) & src_dwords[0xE]
                        ^ (uVar25 & 0xC7ED3902 ^ 0x84EC8112) & uVar64
                        ^ uVar25 & 0xD6A03F00
                        ^ 0xC44D9610
                    )
                    & src_dwords[0xD]
                    ^ ((uVar25 ^ 0xBFFFEFBF) & uVar64 & 0xE0901044 ^ uVar25 & 0xD08012C4 ^ 0xE0101200) & src_dwords[0xE]
                    ^ (src_dwords[0x17] & 0x46A02141 ^ 0x4A0C100) & uVar64
                    ^ src_dwords[0x17] & 0x4EA027C1
                    ^ 0x44008601
                )
                & uVar74
                ^ 0xDBBFFFFF
            )
            & uVar37
        )
        ^ (((uVar47 ^ uVar33) & uVar64 ^ (uVar88 ^ 0x62552042) & uVar25 ^ uVar60 ^ 0xE5430802) & uVar74 ^ 0xE7FF3947) & uVar39
    ) & 0xFFFFFFFF
    uVar40 = (
        (
            (
                (~(src_dwords[0x13] & 0xFFFFFFF7) ^ src_dwords[0x14] & 0x2A) & src_dwords[0x12]
                ^ (~src_dwords[0] ^ src_dwords[0x14]) & 8
                ^ ~(src_dwords[0] & 0xFFFFFFDD)
            )
            & 0x2110003A
            ^ (src_dwords[0x14] & 0x2110001A ^ 0x20000022) & src_dwords[0x13]
        )
        & src_dwords[2]
        ^ (
            ((src_dwords[0x14] ^ 0xED7F7FFF) & 0x9280A008 ^ src_dwords[0x13] & 0x90810500) & src_dwords[0x12]
            ^ ((src_dwords[0x14] ^ 0x12808400) & src_dwords[0x13] ^ src_dwords[0x14] ^ 0xED7F7BFF) & 0x9281A508
            ^ (src_dwords[2] & 0xB390A03A ^ 0x10812508) & src_dwords[0]
            ^ src_dwords[2] & 0x1100038
        )
        & src_dwords[1]
    ) & 0xFFFFFFFF
    uVar89 = (~(src_dwords[0x20] & 0xD56E5E5E) & src_dwords[0x1F]) & 0xFFFFFFFF
    uVar5 = (src_dwords[0xE]) & 0xFFFFFFFF
    uVar48 = (
        (
            (~(uVar5 & 0xF1F056C4) ^ src_dwords[0x20] & 0xD56E5E5E) & src_dwords[0xD] & 0xBE9FB9BB
            ^ (uVar73 & 0x950E181E ^ 0x4F6EEFDF) & uVar5
            ^ ~(uVar73 & 0xFFFE1E1F) & 0x409E9F6
        )
        & src_dwords[0xC]
        ^ (~(uVar73 & 0xB71EB99E) & uVar5 & 0xDDEB5E7F ^ ~(uVar73 & 0xBD1E58FF) & 0xD7EDBF12) & src_dwords[0xD]
        ^ ((~(uVar73 & 0x20900084) ^ uVar27 & 0xBFFFFDBB) & uVar5 & 0xFAF1F7E5 ^ uVar73) & 0xF59E1ADE
        ^ (uVar89 & 0xBE9FB9BB ^ uVar73 & 0x6E68EFD7 ^ 0x409E9F6) & uVar92
        ^ (uVar73 & 0xDDFD5EF3 ^ 0xD7EDBF12) & uVar55
    ) & 0xFFFFFFFF
    uVar54 = (src_dwords[5]) & 0xFFFFFFFF
    uVar56 = (src_dwords[4]) & 0xFFFFFFFF
    uVar10 = ((uVar54 & 0x3CF7DF3A ^ 0x111CDE2A) & uVar56) & 0xFFFFFFFF
    uVar53 = (src_dwords[0x23]) & 0xFFFFFFFF
    uVar11 = ((uVar54 & 0xCF7DD06 ^ 0x11CDC02) & uVar56) & 0xFFFFFFFF
    uVar72 = (src_dwords[0x21]) & 0xFFFFFFFF
    uVar12 = ((uVar54 ^ 0x100092AB) & uVar56 & 0x944292AB) & 0xFFFFFFFF
    uVar13 = ((uVar54 & 0x84160217 ^ 0x1140203) & uVar56) & 0xFFFFFFFF
    uVar34 = (uVar54 & 0x67FF3942 ^ uVar56 & 0x5BBFFF7A ^ 0x24FEC13A) & 0xFFFFFFFF
    uVar14 = (src_dwords[5] & 0x5FF1946) & 0xFFFFFFFF
    uVar35 = (src_dwords[5] & 0xC4423003 ^ uVar56 & 0xD002B2AB ^ 0x8442802A) & 0xFFFFFFFF
    uVar5 = (src_dwords[5]) & 0xFFFFFFFF
    uVar15 = (uVar5 & 0xE45F1001) & 0xFFFFFFFF
    uVar58 = (src_dwords[3]) & 0xFFFFFFFF
    uVar27 = (src_dwords[4] & 0x99181AEF) & 0xFFFFFFFF
    uVar16 = (uVar27 ^ uVar5 & 0xA1181847 ^ 0xA018002E) & 0xFFFFFFFF
    uVar17 = ((uVar54 & 0xB8101AAF ^ 0x11181AAB) & src_dwords[4]) & 0xFFFFFFFF
    uVar18 = (uVar54 & 0x98001AC5) & 0xFFFFFFFF
    uVar49 = (
        (
            ((uVar54 ^ 0x4CCA3) & uVar56 & 0xACE7CDB7 ^ uVar54 & 0xCEA22DC5 ^ 0xE4478411) & uVar53
            ^ (uVar18 ^ uVar17 ^ 0xA0181201) & uVar72
            ^ (uVar54 & 0x81008B4 ^ 0x11808A0) & uVar56
            ^ uVar54 & 0x4A0028C4
            ^ 0x40180010
        )
        & uVar38
        ^ (
            (
                (uVar54 & 0xE6E72947 ^ uVar56 & 0xCAA7EDF7 ^ 0xA4E6C136) & uVar53
                ^ (uVar54 & 0xF7FFFF4F ^ uVar56 ^ 0x180034) & 0x4B1828F4
                ^ uVar16 & uVar72
            )
            & uVar38
            ^ uVar27
            ^ uVar5 & 0xA1181847
            ^ 0xA018002E
        )
        & uVar58
        ^ uVar18
        ^ uVar17
        ^ 0xA0181201
    ) & 0xFFFFFFFF
    uVar78 = (
        (
            (
                (
                    (uVar34 & uVar53 ^ uVar14 ^ uVar56 & 0x9BFDD46 ^ 0x4FEC106) & uVar72
                    ^ uVar35 & uVar53
                    ^ uVar56 & 0x81162217
                    ^ uVar5 & 0x85162007
                    ^ 0x84160016
                )
                & uVar38
                ^ (uVar15 ^ 0xBFFEE9FE) & uVar56
                ^ uVar54 & 0xE7FF3947
                ^ 0xA4FEC13E
            )
            & uVar58
            ^ (
                ((uVar54 & 0x5EA23F40 ^ uVar10 ^ 0x645F9610) & uVar53 ^ uVar54 & 0xCA21D44 ^ uVar11 ^ 0x45F9400) & uVar72
                ^ (uVar54 & 0xD4023281 ^ uVar12 ^ 0xC4429201) & uVar53
                ^ uVar54 & 0x84022205
                ^ uVar13
                ^ 0x84160211
            )
            & uVar38
            ^ (uVar54 & 0xDCA25FAF ^ 0xF55FDEBB) & uVar56
            ^ uVar54 & 0xDEA23FC5
            ^ 0xE45F9611
        )
        & uVar74
        ^ (uVar49 & uVar74 ^ 0xB9181AEF) & src_dwords[0x22]
        ^ uVar56 & 0xE45F9611
    ) & 0xFFFFFFFF
    uVar27 = (src_dwords[0x20]) & 0xFFFFFFFF
    uVar45 = (src_dwords[0xE]) & 0xFFFFFFFF
    uVar50 = (src_dwords[0x1F]) & 0xFFFFFFFF
    uVar22 = (src_dwords[0x20]) & 0xFFFFFFFF
    uVar57 = (src_dwords[2]) & 0xFFFFFFFF
    uVar67 = (
        (
            (
                (
                    (((uVar77 ^ 0xFF7FFF7F) & 0xDFFFFFFF ^ uVar67 ^ uVar27) & uVar45 & 0xFBF1F7E5 ^ uVar27) & 0xF5FE5EDE
                    ^ (uVar27 & 0x2E08A993 ^ uVar89 ^ 0x409A9B2) & src_dwords[0x1E]
                    ^ 0x2A80A181
                )
                & 0xBE9FB9BB
                ^ (uVar27 & 0x9C9D18B3 ^ 0x968DB912) & src_dwords[0x1F]
            )
            & src_dwords[0xD]
            ^ (
                ((uVar9 ^ 0xE0EA99B) & src_dwords[0x1F] ^ (src_dwords[0x20] ^ 0x408E9D6) & 0xDE68FFD7) & src_dwords[0x1E]
                ^ (src_dwords[0x20] & 0x4D6C4ED3 ^ 0x476CAF12) & src_dwords[0x1F]
                ^ src_dwords[0x20] & 0x450E0ADE
                ^ 0xFA60F7C1
            )
            & uVar45
            ^ (
                (~(src_dwords[0x20] & 0xFFFE5E5F) & src_dwords[0x1F] & 0xFFFFBFBB ^ ~(src_dwords[0x20] & 0xFFFEFFDF))
                & src_dwords[0x1E]
                ^ src_dwords[0x20] & 0xFFFE1EDF
                ^ 0xE1C0
            )
            & 0x409E9F6
            ^ (src_dwords[0x20] & 0x40948F2 ^ 0x409A912) & uVar50
        )
        & src_dwords[0xC]
        ^ (
            (
                (~(src_dwords[0x20] & 0xF77EFFDE) & uVar50 & 0x9C8B183B ^ src_dwords[0x20] & 0x4C684E57 ^ 0x4094876) & uVar92
                ^ (uVar73 ^ 0xF7FFBF9E) & uVar50 & 0xDDE95E73
                ^ uVar73 & 0xD58A1A5E
                ^ 0x48F046C1
            )
            & uVar45
            ^ ((~(uVar73 & 0xFD7E5EFF) & uVar55 ^ 0x409A912) & 0x968DB912 ^ uVar73 & 0x4668AF12) & uVar92
            ^ (~(uVar73 & 0xFDFF5EFF) & uVar55 ^ uVar73 & 0xFD9E5AFF ^ 0x42E0A700) & 0xD7EDBF12
        )
        & src_dwords[0xD]
        ^ (
            ((src_dwords[0x20] ^ 0x44) & 0x40000244 ^ uVar59 & src_dwords[0x1F] & 0x90101000) & src_dwords[0x1E]
            ^ ((src_dwords[0x20] ^ 0xFFEFFFBF) & src_dwords[0x1F] & 0xFFFFFFFB ^ src_dwords[0x20]) & 0xD0101244
            ^ 0x608002C0
        )
        & uVar45
        ^ ((uVar9 ^ 0x2A80A181) & src_dwords[0x1F] ^ (uVar22 ^ 0xE1C0) & 0xFB66F7C9) & src_dwords[0x1E]
        ^ (uVar22 & 0x48E646CD ^ 0x42E0A700) & src_dwords[0x1F]
        ^ uVar22 & 0x658E0ADA
        ^ 0x951F183E
    ) & 0xFFFFFFFF
    uVar50 = (~(uVar57 & 8)) & 0xFFFFFFFF
    uVar9 = (uVar63 & uVar50) & 0xFFFFFFFF
    uVar27 = (src_dwords[1]) & 0xFFFFFFFF
    uVar45 = (src_dwords[2]) & 0xFFFFFFFF
    uVar22 = (src_dwords[8]) & 0xFFFFFFFF
    uVar59 = (
        (
            (
                (
                    (uVar41 & 0xB1900032 ^ 0x10810500) & uVar71
                    ^ (uVar57 ^ 0x10802008) & uVar63 & 0x9280A02A
                    ^ (uVar57 ^ 0x2008) & 0xA110203A
                )
                & uVar52
                ^ ((uVar41 & 0xB390A01A ^ 0x10812508) & uVar63 ^ uVar41 & 0x32808022 ^ 0x10800400) & uVar71
                ^ (uVar41 & 0x9280A008 ^ 0x10812508) & uVar63
                ^ uVar57 & 0x8280A000
                ^ 0xFD5E6FF6
            )
            & uVar27
            ^ ((~uVar71 & uVar52 ^ (uVar63 ^ 0xFEEFFFEF) & uVar71) & 0x21100010 ^ 0xDEEEFAAF) & src_dwords[2]
            ^ 0xA15070FA
        )
        & src_dwords[0]
        ^ (
            ((src_dwords[2] & 0x28 ^ 0x90002000) & src_dwords[0x14] ^ src_dwords[2] & 0x1100038 ^ 0x80002000) & uVar27
            ^ ((uVar45 & 0x1100030 ^ 0x90010400) & uVar27 ^ 0xFDDF4FF6) & uVar71
            ^ (uVar63 & 0xDEEEFAAF ^ 0xA15070FA) & uVar50
        )
        & uVar52
        ^ (((uVar45 & 0x1100018 ^ 0x90012400) & uVar63 ^ uVar45 & 0x20 ^ 0x10000400) & uVar27 ^ uVar9 & 0xFBF5F7DB ^ 0x32E8CCE7)
        & uVar71
        ^ ((uVar57 & 8 ^ 0x90012400) & uVar63 ^ uVar45 & 0xFBF5F7DB ^ 0xB2E9ECE7) & uVar27
        ^ (uVar45 ^ uVar9) & 0x9683A508
    ) & 0xFFFFFFFF
    uVar57 = (src_dwords[6]) & 0xFFFFFFFF
    uVar90 = ((src_dwords[7] ^ uVar22 ^ 0xDCFFFEFA) & uVar57) & 0xFFFFFFFF
    uVar50 = (uVar22 & 0x63000201) & 0xFFFFFFFF
    uVar9 = ((uVar50 ^ 0xD818A7DC) & src_dwords[7]) & 0xFFFFFFFF
    uVar41 = (src_dwords[0x1A]) & 0xFFFFFFFF
    uVar68 = ((uVar22 & 0x33188111 ^ 0x501803D0) & src_dwords[7]) & 0xFFFFFFFF
    uVar27 = (src_dwords[7]) & 0xFFFFFFFF
    uVar45 = (src_dwords[7]) & 0xFFFFFFFF
    uVar77 = (
        (
            (
                ((uVar22 & 0x8104 ^ uVar90 ^ 0xEFE77E2B) & 0x731883D5 ^ uVar68) & uVar41
                ^ (src_dwords[8] & 0x731883D5 ^ uVar9 ^ 0x5018A6D8) & uVar57
                ^ (src_dwords[8] & 0x9858E138 ^ 0xFB5847F1) & src_dwords[7]
                ^ src_dwords[8] & 0x8840C124
                ^ 0x9818A1DC
            )
            & src_dwords[0x19]
            ^ (
                (~(src_dwords[8] & 0xEFE77F2F) & src_dwords[7] & 0x731882D1 ^ (src_dwords[8] ^ 0xFF5AF7FF) & 0x54BF9AD2) & uVar57
                ^ (src_dwords[8] & 0x37BF9813 ^ 0x73BD0AD1) & src_dwords[7]
                ^ src_dwords[8] & 0xA69802
                ^ 0x331C81D7
            )
            & uVar41
            ^ (
                (~(src_dwords[8] & 0xEFE75B27) & uVar27 & 0xFBFDEFFD ^ ~(uVar22 & 0xFFFFDBF7)) & uVar57
                ^ uVar22 & 0x29002
                ^ 0x1018A0DA
            )
            & 0x541AB6DA
            ^ (src_dwords[8] & 0x141AB01A ^ 0x501806D0) & uVar27
        )
        & src_dwords[0x18]
        ^ (
            (
                (~(uVar22 & 0x23000001) & uVar27 & 0xFB1827D9 ^ src_dwords[8] & 0x54BF1BD2 ^ 0x541A36DA) & uVar57
                ^ (src_dwords[8] & 0xBFFF793B ^ 0xFBFD4FF1) & uVar27
                ^ src_dwords[8] & 0x88E65922
                ^ 0xFB1CA31B
            )
            & uVar41
            ^ ((~(uVar22 & 0x40000200) & uVar45 ^ 0x501802D0) & 0xD81803D0 ^ src_dwords[8] & 0x50BD0BD0) & uVar57
            ^ (~(src_dwords[8] & 0xBFFFFD3F) & uVar45 ^ src_dwords[8] & 0xAFE6FD2F ^ 0xBF1EF5FF) & 0xD8FD0BD0
        )
        & src_dwords[0x19]
        ^ (
            ((src_dwords[8] ^ 0xDC5BF7FE) & 0x63A61A03 ^ uVar45 & 0xEB000201) & uVar57
            ^ (src_dwords[8] & 0xABE65823 ^ 0xC8E44A20) & uVar45
            ^ src_dwords[8] & 0x88E65822
            ^ 0xEB048307
        )
        & uVar41
        ^ ((uVar50 ^ 0xBB58E1FD) & uVar45 ^ src_dwords[8] & 0x101C81D6 ^ 0x1018A0DA) & uVar57
        ^ (src_dwords[8] & 0xBB1CA51B ^ 0xBB1C45F1) & uVar45
        ^ src_dwords[8] & 0x88048106
        ^ 0x67E35E21
    ) & 0xFFFFFFFF
    uVar89 = (
        (
            (
                (
                    ((src_dwords[0x10] & 0xB9101ACF ^ uVar85 & 0x7D77FF4A ^ 0xD77DD46) & uVar38 ^ 0x7D77FF4A) & uVar51
                    ^ uVar38 & uVar28
                    ^ 0xB467D70B
                )
                & uVar19
                ^ (
                    (
                        (uVar1 ^ 0x61ADA70) & uVar85
                        ^ (uVar61 & 0xB8080AEF ^ 0x80181A64) & src_dwords[0x10]
                        ^ uVar61 & 0x8ED8D46
                        ^ 0x41AD844
                    )
                    & uVar38
                    ^ uVar1
                    ^ 0x61ADA70
                )
                & uVar51
                ^ (uVar61 & 0x80042217 ^ uVar7 ^ uVar6 ^ 0x84120214) & uVar38
                ^ uVar61 & 0xB0E5870B
                ^ 0x8402D200
            )
            & uVar20
            ^ (
                ((uVar85 & uVar2 ^ uVar84 & uVar31 ^ uVar61 & 0xD9FD042 ^ 0x4E7CC04) & uVar38 ^ uVar61 & 0x6F9FD07A ^ 0x44E7EE00)
                & uVar51
                ^ uVar38 & uVar29
                ^ uVar61 & 0xA487D00B
                ^ 0x84E7C601
            )
            & uVar19
            ^ (
                ((uVar3 ^ 0x290EF320) & uVar85 ^ (uVar61 & 0x11000041 ^ 0xA90812A4) & uVar84 ^ uVar61 & 0x1050140 ^ 0x90ED104)
                & uVar38
                ^ uVar3
                ^ 0x6216DB50
            )
            & uVar51
            ^ (uVar61 & 0x1040011 ^ uVar8 ^ uVar30 ^ 0x81062204) & uVar38
            ^ uVar61 & 0x10050101
            ^ 0xA006D300
        )
        & uVar23
        ^ (uVar51 & uVar26 ^ uVar85 & 0xD442B2AB ^ uVar4 ^ 0x85162217) & uVar38
    ) & 0xFFFFFFFF
    uVar45 = (uVar56 & 0xA0181201 ^ uVar53 & 0x39181A6A) & 0xFFFFFFFF
    uVar27 = ((uVar15 ^ 0x64411601) & uVar58 ^ uVar54 & 0x60558010 ^ 0xE4430010) & 0xFFFFFFFF
    uVar41 = (
        (
            ((uVar45 ^ 0xB00002A9) & uVar72 ^ (uVar56 & 0xE4478411 ^ 0x38001A4C) & uVar53 ^ uVar56 & 0x40180010 ^ 0x88080AE3)
            & src_dwords[0x22]
            ^ ((uVar53 ^ 0x45F9400) & src_dwords[0x21] & 0x645F9610 ^ uVar53 & 0xC4429201 ^ 0x84160211) & uVar56
        )
        & uVar38
        ^ ~(
            (
                (
                    (
                        (uVar58 & uVar34 ^ uVar54 & 0x5EA23F40 ^ uVar10 ^ 0x645F9610) & uVar53
                        ^ (uVar14 ^ uVar56 & 0x9BFDD46 ^ 0x4FEC106) & uVar58
                        ^ uVar54 & 0xCA21D44
                        ^ uVar11
                        ^ 0x45F9400
                    )
                    & src_dwords[0x21]
                    ^ (uVar58 & uVar35 ^ uVar54 & 0xD4023281 ^ uVar12 ^ 0xC4429201) & uVar53
                    ^ (uVar56 & 0x81162217 ^ uVar5 & 0x85162007 ^ 0x84160016) & uVar58
                    ^ uVar54 & 0x84022205
                    ^ uVar13
                    ^ 0x84160211
                )
                & uVar38
                ^ src_dwords[0x22] & uVar49
                ^ uVar56 & uVar27
            )
            & uVar74
        )
    ) & 0xFFFFFFFF
    uVar7 = (~(uVar22 & 0x8104)) & 0xFFFFFFFF
    uVar5 = (src_dwords[0x19]) & 0xFFFFFFFF
    uVar5 = (
        (
            (
                (~(src_dwords[8] & 0x100) & 0x40000300 ^ (uVar50 ^ 0x104) & uVar57) & src_dwords[7]
                ^ ((uVar7 & 0x101881D4 ^ uVar90) & 0x731883D5 ^ uVar68) & uVar5
                ^ ((uVar57 ^ 0x104) & src_dwords[8] ^ 0x104) & 0x23000105
            )
            & src_dwords[0x18]
            ^ (
                ((uVar22 & 0x23000001 ^ 0x4040C2E0) & src_dwords[7] ^ (src_dwords[8] ^ 0xDCFFFFFE) & 0x630082C1) & uVar57
                ^ (src_dwords[8] & 0x8400 ^ 0x404002C0) & src_dwords[7]
                ^ ~(src_dwords[8] & 0xFFFFFF3F) & 0x80C0
            )
            & uVar5
            ^ (
                (~src_dwords[8] & 0xFFBFBFDF ^ src_dwords[7]) & uVar57
                ^ ~(src_dwords[8] & 0xFFBFFF3F) & src_dwords[7] & 0xFFFFBFDF
            )
            & 0x105840F0
            ^ 0x63008305
        )
        & src_dwords[0x1A]
        ^ (
            (
                ((uVar50 ^ 0x23404021) & uVar57 ^ src_dwords[8] & 0x23000401 ^ 0x40400200) & uVar5
                ^ (uVar57 & 0x40000200 ^ 0x400) & src_dwords[8]
                ^ 0x40000200
            )
            & src_dwords[0x18]
            ^ ((uVar22 & 0x40000200 ^ 0x400000) & uVar57 ^ 0x40400200) & uVar5
            ^ 0x63404621
        )
        & src_dwords[7]
    ) & 0xFFFFFFFF
    uVar50 = (src_dwords[0x1C]) & 0xFFFFFFFF
    uVar13 = (
        (
            (~(src_dwords[4] & 0xE45F9695) & src_dwords[0x23] & 0x7FFFFF7A ^ ~(src_dwords[4] & 0x45F9400) & 0xDFFDD46)
            & src_dwords[0x21]
            ^ ~(src_dwords[4] & 0xEFFFDF55) & src_dwords[0x23] & 0xD442B2AB
            ^ ~(src_dwords[4] & 0xFEFFDFF9) & 0x85162217
        )
        & src_dwords[0x29]
        ^ (
            (
                (uVar45 ^ 0x9181846) & src_dwords[0x21]
                ^ (uVar56 & 0xE4478411 ^ 0xD6E7F7BB) & src_dwords[0x23]
                ^ uVar56 & 0x40180010
                ^ 0xC3102217
            )
            & src_dwords[0x29]
            ^ (uVar16 & src_dwords[3] ^ uVar18 ^ uVar17 ^ 0xA0181201) & src_dwords[0x25]
            ^ 0xB9181AEF
        )
        & src_dwords[0x22]
        ^ (src_dwords[0x25] & uVar27 ^ 0xE45F9611) & src_dwords[4]
    ) & 0xFFFFFFFF
    uVar6 = (
        (
            ((uVar50 ^ 0x50040001) & 0xDAECAAAF ^ src_dwords[0x1D] & 0xCE8ED0AB) & src_dwords[0x1B]
            ^ (src_dwords[0x1D] & 0xDC66FA8F ^ 0x860ADA24) & uVar50
            ^ src_dwords[0x1D] & 0xC4E6EA05
            ^ 0x18EA70AF
        )
        & src_dwords[0x27]
        ^ src_dwords[1] & 0xF8CD0FF6
    ) & 0xFFFFFFFF
    uVar12 = (
        (
            (uVar50 & 0xFAE5A7DB ^ uVar24 & 0xEB95D0DB ^ 0x51050151) & uVar36
            ^ (uVar24 & 0xF975F7CB ^ 0x8210D250) & uVar50
            ^ uVar24 & 0xC0E5E601
            ^ 0x18F1748B
        )
        & uVar23
    ) & 0xFFFFFFFF
    uVar11 = (
        (
            ((uVar50 ^ 0x10010100) & 0x9281A508 ^ uVar24 & 0x86838008) & uVar36
            ^ (uVar24 & 0x9403A508 ^ 0x86028000) & uVar21
            ^ uVar24 & 0x8483A400
            ^ 0x10832408
        )
        & uVar23
    ) & 0xFFFFFFFF
    uVar27 = (
        ~(
            (
                (
                    (
                        (
                            (uVar24 & 0xED9F40F2 ^ uVar50 & 0xF8CD0FF6 ^ 0x51050150) & uVar36
                            ^ (uVar24 & 0xFD574FC6 ^ 0x841A4A74) & uVar21
                            ^ uVar24 & 0xC4C74E04
                            ^ 0x18DB44A6
                        )
                        & uVar23
                        ^ 0xFDDF4FF6
                    )
                    & src_dwords[1]
                    ^ (
                        ((uVar24 ^ 0x1000050) & 0xA11050FA ^ uVar50 & 0xA04020FA) & uVar36
                        ^ (uVar24 & 0xA15070CA ^ 0x80105070) & uVar21
                        ^ uVar24 & 0x80406000
                        ^ 0x5070AA
                    )
                    & uVar23
                    ^ 0xA15070FA
                )
                & src_dwords[0]
                ^ (
                    (
                        ((uVar50 ^ 0x10000041) & 0x32E88CE7 ^ uVar24 & 0x2288C0E3) & uVar36
                        ^ (uVar24 & 0x3060CCC7 ^ 0x208C864) & uVar21
                        ^ uVar24 & 0xE0CC05
                        ^ 0x10E844A7
                    )
                    & uVar23
                    ^ 0x32E8CCE7
                )
                & src_dwords[1]
                ^ (
                    (uVar24 & 0x6112003A ^ uVar50 & 0x7020053E ^ 0x51000110) & uVar36
                    ^ (uVar24 & 0x7132050E ^ 0x120034) & uVar21
                    ^ uVar24 & 0x40220404
                    ^ 0x1032042E
                )
                & uVar23
                ^ 0x7132053E
            )
            & uVar86
        )
        ^ (
            ((uVar12 ^ 0x33F8DCE7) & src_dwords[1] ^ (uVar6 ^ 0xA44270FA) & src_dwords[0] ^ uVar11 ^ 0x7422053E)
            & src_dwords[0x24]
            ^ 0xFAEDAFFF
        )
        & src_dwords[2]
        ^ uVar23 & 0xFAEDAFFF
    ) & 0xFFFFFFFF
    uVar8 = (
        (src_dwords[0xD] & 0xA69F3903 ^ src_dwords[0xE] & 0xE76E3947 ^ 0x4092946) & src_dwords[0xC]
        ^ (src_dwords[0xE] & 0xC5FB1847 ^ 0xC7ED3902) & src_dwords[0xD]
        ^ src_dwords[0xE] & 0xE0901044
    ) & 0xFFFFFFFF
    uVar10 = ((uVar8 ^ 0x851F1806) & uVar37) & 0xFFFFFFFF
    uVar45 = (src_dwords[0xE]) & 0xFFFFFFFF
    uVar45 = (
        (
            (
                (~uVar45 & src_dwords[0xD] ^ uVar45 ^ 0xFFBFFFFF) & 0x4400000
                ^ ((src_dwords[0xD] ^ 0x4000000) & 0xFFBFFFFF ^ uVar45) & src_dwords[0xC]
                ^ uVar45
            )
            & 0x24400000
            ^ ((uVar25 & 0xC3BF3947 ^ 0x80BEC13E) & uVar64 ^ uVar25 & 0xDAA23FC5 ^ 0xC01F9611) & uVar74
        )
        & uVar37
        ^ (
            (
                (uVar37 & 0xDBBFFFFF ^ uVar47) & uVar64
                ^ (uVar37 & 0x98B7DFBF ^ 0x62552042) & uVar25
                ^ uVar37 & 0x111CDEAB
                ^ 0xE5430802
            )
            & uVar74
            ^ uVar10
        )
        & uVar39
    ) & 0xFFFFFFFF
    uVar1 = (src_dwords[1]) & 0xFFFFFFFF
    uVar2 = (src_dwords[0x1D]) & 0xFFFFFFFF
    uVar3 = (src_dwords[5]) & 0xFFFFFFFF
    uVar4 = (src_dwords[4]) & 0xFFFFFFFF
    uVar50 = (
        (
            (
                (
                    ((uVar50 & 0xF8CD0FF6 ^ 0x51050150) & src_dwords[1] ^ uVar50 & 0xA04020FA ^ 0x1000050) & src_dwords[0]
                    ^ src_dwords[1] & (uVar50 ^ 0x10000041) & 0x32E88CE7
                    ^ uVar50 & 0x7020053E
                    ^ 0x51000110
                )
                & uVar86
                ^ (((uVar1 & 0xED9F40F2 ^ 0xA11050FA) & src_dwords[0] ^ uVar1 & 0x2288C0E3 ^ 0x6112003A) & uVar86 ^ 0x5125000)
                & uVar2
                ^ 0x1000000
            )
            & src_dwords[0x1B]
            ^ (
                (
                    ((uVar1 & 0xFD574FC6 ^ 0xA15070CA) & src_dwords[0] ^ uVar1 & 0x3060CCC7 ^ 0x7132050E) & src_dwords[0x24]
                    ^ 0x5125000
                )
                & uVar2
                ^ ((uVar1 & 0x841A4A74 ^ 0x80105070) & src_dwords[0] ^ uVar1 & 0x208C864 ^ 0x120034) & src_dwords[0x24]
                ^ 0x4125000
            )
            & src_dwords[0x1C]
            ^ (((uVar1 & 0xC4C74E04 ^ 0x80406000) & src_dwords[0] ^ uVar1 & 0xE0CC05 ^ 0x40220404) & src_dwords[0x24] ^ 0x4024000)
            & uVar2
            ^ ((uVar1 & 0x18DB44A6 ^ 0x5070AA) & src_dwords[0] ^ uVar1 & 0x10E844A7 ^ 0x1032042E) & src_dwords[0x24]
            ^ 0xFAFFFFFF
        )
        & src_dwords[0x27]
        ^ ~(
            (
                ((uVar6 ^ 0x7AAC8A55) & src_dwords[0] ^ (uVar12 ^ 0xC80D2B3C) & uVar1 ^ uVar11 ^ 0xE2A1A036) & src_dwords[0x24]
                ^ uVar42 & src_dwords[0x27]
                ^ 0xFAEDAFFF
            )
            & src_dwords[2]
        )
    ) & 0xFFFFFFFF
    uVar34 = ((uVar3 ^ 0x141803) & uVar4) & 0xFFFFFFFF
    uVar79 = (uVar3 ^ uVar4 & 0xDBBFFFFF) & 0xFFFFFFFF
    uVar68 = ((uVar4 & 0x149601 ^ 0x1C0600) & uVar3) & 0xFFFFFFFF
    uVar1 = (src_dwords[0x1A]) & 0xFFFFFFFF
    uVar2 = (src_dwords[7]) & 0xFFFFFFFF
    uVar69 = (
        (
            ((src_dwords[0x17] ^ 0xDBABE7FC) & 0xA4F71907 ^ src_dwords[3] & 0x1C9601) & src_dwords[0x16]
            ^ (src_dwords[3] & 0x1C1001 ^ 0x20550002) & src_dwords[0x17]
            ^ (uVar79 & 0xA4F71907 ^ 0xA4EA8106) & src_dwords[3]
            ^ (uVar3 & 0xDFAAFFFD ^ uVar34 ^ 0x11801) & 0xA4F71907
        )
        & src_dwords[0x15]
        ^ ((~(src_dwords[0x17] & 0xFFF7FFFF) & src_dwords[0x16] ^ ~src_dwords[0x17] & 0x1601) & 0x1C9601 ^ uVar68) & src_dwords[3]
    ) & 0xFFFFFFFF
    uVar6 = (src_dwords[8]) & 0xFFFFFFFF
    uVar35 = (
        (
            (~(uVar1 & 0x731883D5) ^ uVar2 & 0x63404621) & src_dwords[0x19] & 0xFB58E7FD
            ^ (uVar2 & 0x63000201 ^ 0x54BF9AD2) & uVar1
            ^ ~(uVar2 & 0xEBE54F25) & 0x541AB6DA
        )
        & src_dwords[0x18]
        ^ ~(((uVar90 & 0x731883D5 ^ uVar7) & 0xFBFEDBF7 ^ (uVar22 & 0x33188111 ^ 0x505843F0) & uVar2) & uVar1)
        ^ ((uVar2 & 0x23404421 ^ 0xDCFF7FFA) & uVar1 ^ ~(uVar2 & 0x40400200) & 0xD8FD0BD0) & src_dwords[0x19]
        ^ (uVar6 & 0x77BF9BD7 ^ uVar9 ^ 0x541AB6DA) & uVar57
        ^ (uVar6 & 0x9CFFF93A ^ 0xFBFD4FF1) & uVar2
        ^ uVar6 & 0x88E6D926
    ) & 0xFFFFFFFF
    uVar80 = ((uVar2 & 0x9118003C ^ uVar6 & 0x151F1816 ^ 0x141A101A) & uVar57) & 0xFFFFFFFF
    uVar29 = ((uVar6 ^ 0xFAFDEFD5) & uVar2) & 0xFFFFFFFF
    uVar42 = (uVar6 & 0x80061826) & 0xFFFFFFFF
    uVar1 = (src_dwords[8]) & 0xFFFFFFFF
    uVar30 = (
        (
            (
                (
                    (uVar6 & 0x369F9993 ^ uVar2 & 0xBA18A1B9 ^ 0x141AB09A) & uVar57
                    ^ (src_dwords[8] & 0xBE9FB93B ^ 0x989D0990) & uVar2
                    ^ src_dwords[8] & 0x88869922
                    ^ 0x3299A8BB
                )
                & src_dwords[0x1F]
                ^ (uVar2 & 0x8E1F4 ^ src_dwords[8] & 0x40989D6 ^ 0x408A0D2) & uVar57
                ^ (src_dwords[8] & 0x409E932 ^ 0x909D0) & uVar2
                ^ src_dwords[8] & 0xC926
                ^ 0x9E8F2
            )
            & src_dwords[0x1E]
            ^ (
                (uVar2 & 0xD348A710 ^ src_dwords[8] & 0x57AD9B12 ^ 0x5408B612) & uVar57
                ^ (src_dwords[8] & 0x97EDBD12 ^ 0xD0ED0B10) & uVar2
                ^ src_dwords[8] & 0x80E49902
                ^ 0x13E9A812
            )
            & uVar55
            ^ (uVar29 ^ 0x1119083A) & 0x951F183A
            ^ uVar42
            ^ uVar80
        )
        & uVar37
    ) & 0xFFFFFFFF
    uVar9 = (
        (uVar1 & 0x55BB1AD7 ^ uVar2 & 0xD95846FD ^ 0x541A16DA) & uVar57
        ^ (src_dwords[8] & 0x9DFB5C3B ^ 0xD8F90AD0) & uVar2
        ^ src_dwords[8] & 0x88E25826
        ^ 0x11F948FB
    ) & 0xFFFFFFFF
    uVar11 = (((src_dwords[8] ^ 0xDF7FFFFB) & 0x709012C4 ^ uVar2 & 0xF01002C4) & uVar57) & 0xFFFFFFFF
    uVar28 = (
        (uVar1 & 0x772E9BD7 ^ uVar2 & 0xFB48E7DD ^ 0x540AB6DA) & uVar57
        ^ (uVar1 & 0xBF6EFD1B ^ 0xD86C0BD0) & uVar2
        ^ uVar1 & 0x8866D906
        ^ 0x3368E8DB
    ) & 0xFFFFFFFF
    uVar2 = ((src_dwords[8] & 0xB0901000 ^ 0xD09002C0) & uVar2) & 0xFFFFFFFF
    uVar1 = (src_dwords[0x26]) & 0xFFFFFFFF
    uVar81 = (
        (
            (
                (uVar28 & uVar1 ^ uVar55 & 0x941F183A ^ 0x6E69EFF7) & src_dwords[0x1E]
                ^ (uVar9 & uVar1 ^ 0xDDED5ED3) & src_dwords[0x1F]
                ^ (src_dwords[8] & 0x80801004 ^ uVar2 ^ uVar11 ^ 0x309000C0) & uVar1
                ^ 0xF59F1AFE
            )
            & src_dwords[0x28]
            ^ 0x951F183E
        )
        & src_dwords[0x20]
        ^ ((src_dwords[0x1F] & 0xBE9FB9BB ^ 0x409E9F6) & src_dwords[0x1E] ^ src_dwords[0x1F] & 0xD7EDBF12 ^ 0x951F183E)
        & src_dwords[0x28]
        ^ ~((uVar30 ^ 0x541AB6DA) & uVar1)
    ) & 0xFFFFFFFF
    uVar1 = (src_dwords[0xE]) & 0xFFFFFFFF
    uVar6 = (src_dwords[0xD]) & 0xFFFFFFFF
    uVar33 = (
        (
            (
                (
                    (uVar6 & 0xA49E813A ^ uVar1 & 0xA46EC11E ^ 0x408C136) & src_dwords[0xC]
                    ^ (uVar1 & 0x84FA403E ^ 0x84EC8112) & uVar6
                    ^ uVar1 & 0xA0900004
                    ^ 0x4A0C100
                )
                & src_dwords[0x28]
                ^ ((uVar8 ^ 0x46A02141) & src_dwords[0x28] ^ 0xE7FF3947) & src_dwords[0x17]
                ^ 0xA4FEC13E
            )
            & src_dwords[0x15]
            ^ (
                (
                    ((uVar1 ^ 0x40029C4) & 0xDE223FC5 ^ uVar6 & 0x9E823981) & src_dwords[0xC]
                    ^ (uVar1 & 0xDCA21EC5 ^ 0xD6A03F00) & uVar6
                    ^ uVar1 & 0xD08012C4
                    ^ 0x4EA027C1
                )
                & src_dwords[0x28]
                ^ 0xDEA23FC5
            )
            & src_dwords[0x17]
            ^ (
                ((uVar6 ^ 0x4098010) & 0xA41F9011 ^ uVar1 & 0xE44E9611) & src_dwords[0xC]
                ^ (uVar1 & 0xC45B1611 ^ 0xC44D9610) & uVar6
                ^ uVar1 & 0xE0101200
                ^ 0x44008601
            )
            & src_dwords[0x28]
            ^ 0xE45F9611
        )
        & src_dwords[0x25]
        ^ (
            (
                (src_dwords[0x17] & 0xE7FF3947 ^ uVar33 ^ 0xBCFEC7BE) & src_dwords[0x15]
                ^ (uVar88 ^ 0xDEA2FFFD) & src_dwords[0x17]
                ^ uVar60
                ^ 0xF45FD6A9
            )
            & src_dwords[0x25]
            ^ uVar10
            ^ 0xE7FF3947
        )
        & src_dwords[0x16]
        ^ uVar33
    ) & 0xFFFFFFFF
    uVar1 = (src_dwords[0x1A]) & 0xFFFFFFFF
    uVar70 = ((uVar1 & 0x32E8CC23 ^ 0x10E808C0) & src_dwords[0x19]) & 0xFFFFFFFF
    uVar8 = ((uVar1 & 0x32A888C7 ^ src_dwords[0x19] & 0x3248C4E5 ^ 0x100884C2) & src_dwords[0x26]) & 0xFFFFFFFF
    uVar26 = ((uVar1 & 0xE0C826 ^ uVar70 ^ 0x22E04C21) & src_dwords[0x26]) & 0xFFFFFFFF
    uVar60 = (
        ~(
            (
                (
                    (uVar71 & 0x65C34E20 ^ uVar63 & 0x46E25A21 ^ 0x21405020) & uVar52
                    ^ (uVar63 & 0x63E15601 ^ 0x22E04C21) & uVar71
                    ^ uVar63 & 0x6830400
                    ^ uVar8
                    ^ 0x61220420
                )
                & uVar86
                ^ (((uVar1 ^ 0xFBBDEFFF) & src_dwords[0x19] ^ 0xFBFDEBFF) & 0x27E35C21 ^ uVar1 & 0x67414221) & src_dwords[0x26]
            )
            & src_dwords[0x18]
        )
        ^ (
            (src_dwords[0x13] & 0xCD170310 ^ uVar63 & 0xCC063208 ^ 0x81103018) & uVar52
            ^ (src_dwords[0x13] & 0xC9153318 ^ 0x84032108) & uVar63
            ^ uVar26
            ^ 0x41120118
        )
        & uVar86
    ) & 0xFFFFFFFF
    uVar12 = (~uVar67) & 0xFFFFFFFF
    uVar10 = (~uVar5 ^ uVar77) & 0xFFFFFFFF
    uVar49 = (
        (~((uVar45 ^ uVar66) & uVar67) ^ (uVar45 ^ uVar66) & uVar48 ^ uVar45 ^ uVar66) & uVar33
        ^ (~((uVar48 ^ uVar12) & uVar45) ^ uVar67 ^ uVar48) & uVar66
        ^ (~(uVar48 & uVar12) ^ uVar67) & uVar43
        ^ uVar67
    ) & 0xFFFFFFFF
    uVar7 = ((uVar43 ^ uVar12) & uVar48) & 0xFFFFFFFF
    uVar6 = (src_dwords[0x26]) & 0xFFFFFFFF
    uVar6 = (
        (uVar37 & uVar10 ^ uVar6 ^ uVar7 ^ uVar77 ^ uVar43) & uVar35
        ^ (~uVar7 ^ uVar6 ^ uVar77 ^ uVar43) & uVar37
        ^ uVar6
        ^ uVar77
    ) & 0xFFFFFFFF
    uVar19 = (
        ~(
            (
                (~(uVar36 & 0xE29EDB70) ^ uVar24 & 0x82888A74) & uVar19 & 0xFD77FFCF
                ^ (uVar24 & ~uVar61 & 0x871ADA74 ^ uVar61) & 0xFAEDAFFF
                ^ (uVar61 & 0xE0048B40 ^ 0x8012DA40) & uVar36
                ^ 0x861ADA74
            )
            & uVar20
        )
        ^ (
            (uVar61 & 0xE016D040 ^ 0xC006CA00) & uVar36
            ^ (uVar61 & 0x82088070 ^ 0x80008A04) & uVar24
            ^ uVar61 & 0xEF9FD0FB
            ^ 0xC4E7EE05
        )
        & uVar19
        ^ ((uVar24 & 0x621E5134 ^ 0x9AFBFEFF) & uVar21 ^ ~(uVar61 & 0x40040140) & 0xF117DB51 ^ uVar24 & 0x4D874A9B) & uVar36
        ^ (uVar61 & 0x51050151 ^ uVar32) & 0xFF7FFFFF
        ^ uVar24 & ~(uVar61 & 0x50) & 0xC6EFEE75
    ) & 0xFFFFFFFF
    uVar21 = (src_dwords[0x19]) & 0xFFFFFFFF
    uVar14 = ((src_dwords[0x1A] & 0x9EEEF82B ^ 0xD8EC0A80) & uVar21 ^ src_dwords[0x1A] & 0x88E6D826 ^ 0x46E25A21) & 0xFFFFFFFF
    uVar16 = ((src_dwords[0x1A] & 0xBDDF4D32 ^ 0xD8DD0BD0) & uVar21 ^ src_dwords[0x1A] & 0x88C64926 ^ 0x65C34E20) & 0xFFFFFFFF
    uVar20 = ((src_dwords[0x1A] & 0xA150703A ^ 0x805000D0) & uVar21) & 0xFFFFFFFF
    uVar17 = ((src_dwords[0x1A] & 0xBBF5F51B ^ 0xD8F503D0) & uVar21 ^ src_dwords[0x1A] & 0x88E4D102 ^ 0x63E15601) & 0xFFFFFFFF
    uVar18 = ((src_dwords[0x1A] ^ 0xF9FD5BF7) & uVar21 ^ src_dwords[0x1A] & 0xE9FEDBF7 ^ 0x6830400) & 0xFFFFFFFF
    uVar21 = ((src_dwords[0x1A] & 0x3DAC919 ^ 0x40D809D0) & uVar21) & 0xFFFFFFFF
    uVar24 = (src_dwords[0x26]) & 0xFFFFFFFF
    uVar88 = (
        (
            (
                (
                    ((src_dwords[0x1A] & 0x56AE9A87 ^ src_dwords[0x19] & 0xDA48E2AD ^ 0x540AB28A) & src_dwords[0x26] ^ 0x46E25A21)
                    & src_dwords[0x14]
                    ^ (
                        (src_dwords[0x19] & 0xF95847F4 ^ src_dwords[0x1A] & 0x759F0BD6 ^ 0x541A06D2) & src_dwords[0x26]
                        ^ 0x65C34E20
                    )
                    & src_dwords[0x13]
                    ^ (src_dwords[0x19] & 0xA15060F8 ^ src_dwords[0x1A] & 0x211010D2 ^ 0x1030DA) & src_dwords[0x26]
                    ^ 0x21405020
                )
                & src_dwords[0x12]
                ^ (
                    ((src_dwords[0x1A] & 0x73B593D3 ^ src_dwords[0x19] & 0xFB50E7D9 ^ 0x5010B6DA) & src_dwords[0x26] ^ 0x63E15601)
                    & src_dwords[0x14]
                    ^ uVar8
                    ^ 0x22E04C21
                )
                & src_dwords[0x13]
                ^ ((src_dwords[0x19] & 0x9200A508 ^ src_dwords[0x1A] & 0x16838100 ^ 0x1402A408) & uVar24 ^ 0x6830400)
                & src_dwords[0x14]
                ^ (src_dwords[0x1A] & 0x439A89D1 ^ src_dwords[0x19] & 0x4358C1D9 ^ 0x401A80D8) & uVar24
                ^ 0x61220420
            )
            & uVar86
            ^ ((src_dwords[0x1A] & 0x27E35C21 ^ 0xD8F9ABDC) & src_dwords[0x19] ^ src_dwords[0x1A] & 0x10FED9F6 ^ 0x77FBFEFB)
            & uVar24
            ^ 0x67E35E21
        )
        & src_dwords[0x18]
        ^ (
            (
                (uVar24 & uVar16 ^ 0x30C84CE6) & uVar71
                ^ (uVar24 & uVar14 ^ 0x12E8C8A7) & uVar63
                ^ (src_dwords[0x1A] & 0x80405022 ^ uVar20 ^ 0x21405020) & uVar24
                ^ 0x204040E2
            )
            & uVar52
            ^ ((uVar24 & uVar17 ^ 0x32E0C4C3) & uVar63 ^ uVar26 ^ 0x32E8CCE7) & uVar71
            ^ (uVar24 & uVar18 ^ 0x12808400) & uVar63 & 0x9683A508
            ^ (src_dwords[0x1A] & 0xC2C900 ^ uVar21 ^ 0x43C24801) & uVar24
            ^ 0x2C8C8C1
        )
        & uVar86
        ^ ((src_dwords[0x1A] & 0xBFFFFD3B ^ 0xD8FD0BD0) & src_dwords[0x19] ^ src_dwords[0x1A] & 0x88E6D926 ^ 0x67E35E21) & uVar24
    ) & 0xFFFFFFFF
    uVar26 = (((uVar55 & 0x941F183A ^ 0x91071028) & uVar92 ^ uVar55 & 0x16002C ^ 0x50F083A) & uVar37) & 0xFFFFFFFF
    uVar82 = ((uVar29 ^ 0x5031820) & 0x951F183A) & 0xFFFFFFFF
    uVar8 = ((uVar75 ^ uVar44) & uVar89) & 0xFFFFFFFF
    uVar7 = (uVar87 ^ uVar44) & 0xFFFFFFFF
    uVar24 = (
        (
            (
                (uVar9 & uVar55 ^ uVar28 & uVar92 ^ src_dwords[8] & 0x80801004 ^ uVar2 ^ uVar11 ^ 0x309000C0) & uVar37
                ^ uVar42
                ^ uVar80
                ^ uVar82
            )
            & uVar24
            ^ uVar26
        )
        & uVar73
        ^ (
            ((src_dwords[7] & 0xFBFDEFFD ^ ~(uVar22 & 0xFFFFDBF7)) & uVar57 ^ uVar22 & 0x29002 ^ 0xEFE75F25) & 0x541AB6DA
            ^ (src_dwords[8] & 0x141AB41A ^ 0x501802D0) & src_dwords[7]
            ^ uVar30
        )
        & uVar24
    ) & 0xFFFFFFFF
    uVar22 = (~uVar46) & 0xFFFFFFFF
    uVar28 = (
        (~((uVar22 ^ uVar44) & uVar19) ^ (uVar22 ^ uVar75) & uVar44 ^ uVar8 ^ uVar46 ^ uVar75) & uVar87
        ^ (~uVar75 & uVar89 ^ uVar19 & uVar46) & uVar44
    ) & 0xFFFFFFFF
    uVar61 = (uVar10 & uVar35) & 0xFFFFFFFF
    uVar10 = ((~(uVar10 & uVar67) ^ uVar5 ^ uVar77) & uVar35) & 0xFFFFFFFF
    uVar36 = ((src_dwords[0x26] ^ uVar37 ^ uVar61 ^ uVar77) & uVar43) & 0xFFFFFFFF
    uVar2 = (
        ~(((src_dwords[0x26] ^ uVar37 ^ uVar77) & uVar67 ^ src_dwords[0x26] ^ uVar37 ^ uVar10 ^ uVar36 ^ uVar77) & uVar48)
        ^ (src_dwords[0x26] ^ uVar61 ^ uVar77) & uVar37
        ^ uVar36
        ^ uVar35
    ) & 0xFFFFFFFF
    uVar8 = (~((uVar19 ^ uVar46) & uVar87) ^ ~uVar75 & uVar44 ^ uVar19 & uVar46 ^ uVar8 ^ uVar75) & 0xFFFFFFFF
    uVar29 = (
        ~((~((uVar48 ^ uVar66 ^ uVar43) & uVar67) ^ (uVar66 ^ uVar12) & uVar45 ^ uVar48 ^ uVar43) & uVar33)
        ^ ~uVar45 & uVar67 & uVar66
        ^ uVar48
    ) & 0xFFFFFFFF
    uVar36 = (src_dwords[0x26]) & 0xFFFFFFFF
    uVar9 = ((~uVar61 ^ uVar36 ^ uVar37 ^ uVar77) & uVar43) & 0xFFFFFFFF
    uVar9 = (
        ~(((~uVar37 ^ uVar36 ^ uVar77) & uVar67 ^ ~uVar9 ^ uVar36 ^ uVar37 ^ uVar10 ^ uVar77) & uVar48)
        ^ (~uVar37 ^ uVar36 ^ uVar5) & uVar35
        ^ uVar37
        ^ uVar9
    ) & 0xFFFFFFFF
    uVar10 = (~(_shr((uVar9 ^ uVar2), 1)) & 0x7FFFFFFF) & 0xFFFFFFFF
    uVar36 = ((uVar59 ^ uVar40) & uVar76) & 0xFFFFFFFF
    uVar30 = ((~uVar65 & uVar50 ^ uVar36 ^ uVar59) & uVar27 ^ (uVar36 ^ uVar59) & uVar65 ^ uVar50 ^ uVar76) & 0xFFFFFFFF
    uVar67 = (
        (~((uVar45 ^ uVar67 ^ uVar66) & uVar33) ^ ~uVar45 & uVar66 ^ uVar43 & uVar12) & uVar48
        ^ (~uVar66 & uVar45 ^ uVar43 & uVar12 ^ uVar67) & uVar33
        ^ uVar67
    ) & 0xFFFFFFFF
    uVar90 = (
        ((uVar27 ^ uVar59 ^ uVar40) & uVar50 ^ uVar27 ^ uVar59) & uVar76
        ^ ((~uVar50 ^ uVar76) & uVar27 ^ uVar50 ^ uVar76) & uVar65
        ^ (uVar27 ^ uVar59) & uVar50
        ^ uVar59
    ) & 0xFFFFFFFF
    uVar12 = ((uVar2 ^ uVar6) << 0x1F & 0xFFFFFFFF) & 0xFFFFFFFF
    uVar11 = (~uVar50 ^ uVar65) & 0xFFFFFFFF
    uVar31 = ((~uVar8 ^ uVar65) & uVar7) & 0xFFFFFFFF
    uVar32 = (
        (~(uVar8 & uVar11) ^ ~uVar65 & uVar50 ^ uVar65) & uVar27
        ^ ~((~uVar7 ^ uVar50) & uVar65) & uVar8
        ^ (uVar8 ^ uVar31 ^ uVar65) & uVar28
    ) & 0xFFFFFFFF
    uVar43 = (src_dwords[0x23]) & 0xFFFFFFFF
    uVar62 = (~src_dwords[0x22] & 4 ^ uVar43 & 0x2010) & 0xFFFFFFFF
    uVar91 = (~uVar43) & 0xFFFFFFFF
    uVar36 = (src_dwords[0x22]) & 0xFFFFFFFF
    uVar61 = (src_dwords[0x23]) & 0xFFFFFFFF
    uVar47 = (
        (
            (
                ((~(uVar43 & 0x9181842) & src_dwords[0x22] ^ 0x9181846) & 0xB9181AEF ^ uVar85 & uVar62 ^ uVar43 & 0x39183A7A)
                & uVar72
                ^ (uVar85 & uVar91 & 0x2014 ^ uVar53 & 0xA00030B3 ^ 0x80838F0) & src_dwords[0x22]
                ^ ~(uVar85 & 0x2000) & uVar53 & 0x900032AB
                ^ 0x81100207
            )
            & uVar84
            ^ (
                ((uVar43 & 0xDFFDD42 ^ 0x3CEFDF6A) & src_dwords[0x22] ^ (uVar53 ^ 0xCEFDD42) & 0x7EEFFF6A) & uVar72
                ^ (uVar53 & 0x6642B022 ^ 0x4BF9FD60) & src_dwords[0x22]
                ^ uVar53 & 0x5442B22A
                ^ 0x5162212
            )
            & uVar85
            ^ (((uVar53 ^ 0xFEEFFFFF) & src_dwords[0x22] ^ uVar91 & 0xFEEFFFFF) & uVar72 ^ uVar43 & 0x4429002) & 0xDFFDD42
            ^ (uVar53 & 0x4429006 ^ 0x9F9DD44) & uVar36
            ^ 0x5160006
        )
        & src_dwords[0xF]
        ^ (
            (
                ((~(src_dwords[0x23] & 0xCE7CD42) & uVar36 ^ 0xCE7CD46) & 0xACE7CDE7 ^ src_dwords[0x23] & 0x6EE7ED72) & uVar72
                ^ (uVar53 & 0xE642A0B3 ^ 0x4AE1EDF0) & uVar36
                ^ uVar53 & 0xC442A0A3
                ^ 0x84062017
            )
            & uVar85
            ^ ((~(uVar53 & 0xFFFFFF5B) & src_dwords[0x22] ^ 0xFFFFFF5F) & 0x91808E4 ^ uVar53 & 0x4B182870) & uVar72
            ^ (~(uVar53 & 0xF7F7F7BF) & src_dwords[0x22] ^ uVar53 & 0xF5F7F7AF) & 0x4A0828F0
            ^ 0x1102014
        )
        & uVar84
        ^ (
            ((~(uVar43 & 0x4429002) & src_dwords[0x22] ^ 0x4429002) & 0x944292AB ^ uVar61 & 0x5442B22A) & uVar72
            ^ ((uVar61 ^ 0x4040B0A0) & src_dwords[0x22] & 0xEFFFFDF7 ^ uVar61 ^ 0xAFBF6F57) & 0xD442B2AB
        )
        & uVar85
        ^ ((uVar53 & 0x8E9DD40 ^ 0x81F1C707) & src_dwords[0x22] ^ uVar53 & 0x5162212 ^ 0x5160006) & uVar72
        ^ (src_dwords[0x23] & 0x8CA77D57 ^ 0x1F1F514) & src_dwords[0x22]
        ^ ~(src_dwords[0x23] & 0xFEEBFFEB) & 0x85162217
    ) & 0xFFFFFFFF
    uVar36 = (src_dwords[0x23]) & 0xFFFFFFFF
    uVar48 = ((uVar72 ^ 0xFFFFFFEF) & uVar36) & 0xFFFFFFFF
    uVar61 = (src_dwords[0x22]) & 0xFFFFFFFF
    uVar83 = ((uVar36 ^ 0x4E7C500) & uVar72) & 0xFFFFFFFF
    uVar48 = (
        (
            (
                ((~(uVar36 & 0xFFFFFFEB) ^ src_dwords[0x22] & uVar91) & 0x2014 ^ uVar72 & uVar62) & uVar85
                ^ ((uVar72 & 0x9181842 ^ 0x8003854) & uVar53 ^ 0x8082852) & uVar61
                ^ ~uVar48 & 0x2010
            )
            & src_dwords[0x10]
            ^ (
                (((src_dwords[0x23] ^ 0x5F7C500) & uVar61 ^ 0x1100000) & 0xDFFDD42 ^ src_dwords[0x23] & 0x1100010) & uVar72
                ^ (uVar53 & 0x8A55D50 ^ 0xD1E0852) & uVar61
                ^ 0x1100010
            )
            & uVar85
            ^ (uVar53 & 0x8A57D54 ^ uVar83 & 0xDFFDD42 ^ 0xC0E2852) & uVar61
            ^ uVar48 & 0x2010
            ^ 0x1100004
        )
        & uVar51
        ^ (
            (
                ((uVar83 ^ 0xFF1E3AFF) & 0xCE7CD42 ^ uVar53 & 0x8A54D44) & uVar85
                ^ (uVar72 & 0x9180840 ^ 0x8000844) & uVar53
                ^ 0x8080840
            )
            & uVar84
            ^ ((uVar53 ^ 0xFFFFEFFD) & uVar72 ^ uVar53 & 0x1000 ^ 0xFFBF6FFF) & uVar85 & 0x4429002
            ^ (uVar53 ^ 0xFEEFFFFD) & uVar72 & 0x5160002
            ^ uVar53 & 0x40004
            ^ 0x9F9DD44
        )
        & uVar61
    ) & 0xFFFFFFFF
    uVar51 = (
        (
            (~(uVar61 & 0x9181846) ^ uVar85 & 0x2014) & uVar84 & 0xB9183AFF
            ^ (~src_dwords[0x22] & 0x1100004 ^ uVar53 & 0x1102010) & uVar72
            ^ (uVar53 & 0x2014 ^ 0xCEFFD52) & uVar61
            ^ (uVar61 & 0xDFFDD42 ^ 0x7EEFFF6A) & uVar85
            ^ ~(uVar53 & 0x2000) & 0xDFFFD56
        )
        & uVar51
        ^ (~(uVar61 & 0xCE7CD46) & uVar85 & 0xEEE7EDF7 ^ ~(uVar61 & 0x9180844) & 0x4B1828F4) & uVar84
        ^ ((~(uVar43 & 0xDFFDD42) & uVar61 ^ 0xDFFDD46) & 0xBDFFDFEF ^ uVar53 & 0x7FFFFF7A) & uVar72
        ^ (~(uVar61 & 0x4429002) & uVar85 ^ uVar53) & 0xD442B2AB
        ^ (uVar53 & 0xE642B0B3 ^ 0x4FFFFDF6) & uVar61
    ) & 0xFFFFFFFF
    uVar1 = (
        (
            (
                (
                    (
                        (uVar71 & 0xF95847F4 ^ uVar63 & 0xDA48E2AD ^ 0xA15060F8) & uVar52
                        ^ (uVar63 & 0xFB50E7D9 ^ 0x3248C4E5) & uVar71
                        ^ uVar63 & 0x9200A508
                        ^ 0x4358C1D9
                    )
                    & uVar86
                    ^ (uVar1 ^ 0xFBBDEFFF) & 0x27E35C21
                )
                & src_dwords[0x19]
                ^ (
                    (
                        (src_dwords[0x14] & 0x56AE9A87 ^ src_dwords[0x13] & 0x759F0BD6 ^ 0x211010D2) & uVar52
                        ^ (src_dwords[0x14] & 0x73B593D3 ^ 0x32A888C7) & src_dwords[0x13]
                        ^ src_dwords[0x14] & 0x16838100
                        ^ 0x439A89D1
                    )
                    & src_dwords[0x24]
                    ^ 0x67414221
                )
                & src_dwords[0x1A]
                ^ (
                    (src_dwords[0x13] & 0x541A06D2 ^ src_dwords[0x14] & 0x540AB28A ^ 0x1030DA) & uVar52
                    ^ (src_dwords[0x14] & 0x5010B6DA ^ 0x100884C2) & src_dwords[0x13]
                    ^ src_dwords[0x14] & 0x1402A408
                    ^ 0x401A80D8
                )
                & src_dwords[0x24]
                ^ 0x23E14821
            )
            & src_dwords[0x26]
            ^ 0x67E35E21
        )
        & src_dwords[0x18]
        ^ (
            (
                (src_dwords[0x13] & uVar16 ^ src_dwords[0x14] & uVar14 ^ src_dwords[0x1A] & 0x80405022 ^ uVar20 ^ 0x21405020)
                & src_dwords[0x12]
                ^ (src_dwords[0x14] & uVar17 ^ uVar1 & 0xE0C826 ^ uVar70 ^ 0x22E04C21) & src_dwords[0x13]
                ^ src_dwords[0x14] & uVar18 & 0x9683A508
                ^ src_dwords[0x1A] & 0xC2C900
                ^ uVar21
                ^ 0x43C24801
            )
            & src_dwords[0x26]
            ^ 0x32E8CCE7
        )
        & src_dwords[0x24]
    ) & 0xFFFFFFFF
    uVar43 = (src_dwords[3]) & 0xFFFFFFFF
    uVar14 = (
        ((~uVar47 ^ uVar75) & uVar48 ^ (uVar89 ^ uVar44) & uVar75 ^ uVar89) & uVar51
        ^ (uVar48 & uVar47 ^ uVar44) & uVar75
        ^ uVar48
        ^ uVar47
    ) & 0xFFFFFFFF
    uVar36 = (~(_shr(uVar9, 1)) & _shr(uVar2, 1)) & 0xFFFFFFFF
    uVar36 = (~uVar36 & _shr(uVar6, 1) ^ uVar36) & 0xFFFFFFFF
    uVar21 = (src_dwords[5]) & 0xFFFFFFFF
    uVar71 = (((uVar79 ^ 0xFFFEE7FE) & uVar43 ^ uVar3 & 0xDFAAFFFD ^ uVar34 ^ 0xA00906) & src_dwords[0x17]) & 0xFFFFFFFF
    uVar84 = (~(uVar21 & 0x149601) & uVar56) & 0xFFFFFFFF
    uVar34 = (
        (
            (
                ((uVar21 & 0x141001 ^ 0xC3AA3945) & uVar56 ^ (uVar54 ^ 0xBCFFC7BE) & 0xC7B63945) & uVar43
                ^ (uVar54 & 0x84A21905 ^ 0x1081801) & uVar56
                ^ uVar54 & 0xC6A23945
                ^ 0xE45F1003
            )
            & uVar25
            ^ (
                ((uVar54 & 0xE7E33F47 ^ uVar84 ^ 0x403A) & uVar43 ^ uVar54 & 0xFEE33FC5) & 0x5B1CFEFB
                ^ (uVar54 & 0x1814DEBB ^ 0x111CDEAB) & uVar56
                ^ uVar71 & 0xA4F71907
                ^ 0xC0BF9715
            )
            & uVar39
            ^ ((uVar21 & 0x148000 ^ 0xA8C93E) & uVar56 ^ uVar54 & 0xB40906 ^ 0xB4413E) & uVar43
            ^ (uVar54 & 0xA0C93E ^ 0x8C82A) & uVar56
            ^ uVar54 & 0xA00904
            ^ 0xA99117
        )
        & uVar64
        ^ (
            (
                ((uVar54 ^ 0x1014DEAB) & uVar56 ^ uVar54 & 0xDFAA3FC5 ^ 0xE75FB651) & 0xBCF7DFBF
                ^ (uVar84 & 0x98B7DFBF ^ uVar54 & 0xA4E31F07 ^ 0xA4E2413E) & uVar43
            )
            & uVar25
            ^ ((uVar54 & 0x1001E03 ^ uVar84 ^ 0x402A) & uVar43 ^ ~(uVar54 & 0xFEF7FFFF) & uVar56 ^ uVar54 & 0xFEE33FD5 ^ 0x1C9601)
            & 0x111CDEAB
        )
        & uVar39
        ^ (
            (~(uVar54 & 0x1601) & uVar56 & 0xDAA23FC5 ^ (uVar54 ^ 0xBDFFC1BE) & 0xC6A23F45) & uVar43
            ^ ((uVar54 ^ 0x10001E81) & uVar56 & 0xBDFFDFBF ^ uVar54 ^ 0xE55FD63B) & 0xDEA23FC5
        )
        & uVar25
        ^ (uVar56 & 0xC01F9611 ^ uVar15 ^ 0xA4421611) & uVar43
        ^ (uVar54 & 0xA4579611 ^ 0x1C9601) & uVar56
        ^ uVar54 & 0xC4021601
        ^ 0x1BA069EE
    ) & 0xFFFFFFFF
    uVar72 = (
        ((uVar50 ^ uVar59 ^ uVar40 ^ uVar65) & uVar27 ^ (uVar50 ^ uVar65) & (uVar59 ^ uVar40) ^ uVar40) & uVar76
        ^ (uVar50 ^ uVar27 ^ uVar65) & uVar59
        ^ uVar27
        ^ uVar65
    ) & 0xFFFFFFFF
    uVar63 = (~uVar72) & 0xFFFFFFFF
    uVar84 = (
        ~(((uVar63 ^ uVar60) & uVar1 ^ (uVar1 ^ uVar60) & uVar88 ^ (uVar72 ^ uVar1) & uVar90 ^ uVar60) & uVar30)
        ^ (~(~uVar60 & uVar88) ^ uVar63 & uVar90 ^ uVar72) & uVar1
        ^ uVar72
        ^ uVar88
    ) & 0xFFFFFFFF
    uVar16 = (
        (
            ((uVar55 & 0x141AB09A ^ 0x408A0D2) & uVar92 ^ uVar55 & 0x5408B612 ^ 0x141A101A) & uVar37
            ^ ((src_dwords[8] ^ 0xDCFFBFDE) & 0xABE54921 ^ uVar57 & 0xAB404125) & src_dwords[7]
            ^ (uVar57 & 0x23A50905 ^ 0x88E44924) & src_dwords[8]
            ^ 0x77FBFEFB
        )
        & src_dwords[0x26]
        ^ (
            (((src_dwords[0x1F] ^ 0xFBF5FBE5) & 0x541A16DA ^ uVar92 & 0x540AB6DA) & uVar37 ^ uVar42 ^ uVar80 ^ uVar82)
            & src_dwords[0x26]
            ^ uVar26
            ^ 0x951F183E
        )
        & uVar73
    ) & 0xFFFFFFFF
    uVar11 = (uVar11 & uVar27) & 0xFFFFFFFF
    uVar3 = (
        ((uVar7 ^ uVar50) & uVar65 ^ uVar11 ^ uVar7) & uVar8 ^ ~((uVar8 ^ uVar65) & uVar7) & uVar28 ^ ~(~uVar27 & uVar50) & uVar65
    ) & 0xFFFFFFFF
    uVar52 = (~uVar16) & 0xFFFFFFFF
    uVar37 = (
        ~(((uVar52 ^ uVar24) & uVar5 ^ ~uVar24 & uVar16 ^ uVar24) & uVar81)
        ^ ~((uVar24 ^ uVar77) & uVar5) & uVar16
        ^ (uVar52 ^ uVar5) & uVar35 & uVar77
    ) & 0xFFFFFFFF
    uVar53 = (~uVar60 & uVar1) & 0xFFFFFFFF
    uVar18 = (
        (~((uVar72 ^ uVar60) & uVar1) ^ (~uVar30 ^ uVar60) & uVar72 ^ (uVar63 ^ uVar30) & uVar90) & uVar88
        ^ (~uVar90 & uVar30 ^ uVar53 ^ uVar60) & uVar72
        ^ uVar1
        ^ uVar30
    ) & 0xFFFFFFFF
    uVar85 = (~((~uVar48 ^ uVar47) & uVar51)) & 0xFFFFFFFF
    uVar43 = (uVar85 ^ uVar23 ^ uVar48) & 0xFFFFFFFF
    uVar85 = (
        ~(
            (
                (~((~uVar48 ^ uVar47) & uVar46) ^ uVar48 ^ uVar47) & uVar51
                ^ (~uVar23 ^ uVar48) & uVar46
                ^ ~(uVar43 & uVar87)
                ^ uVar23
                ^ uVar48
            )
            & uVar19
        )
        ^ (uVar85 ^ uVar48) & uVar23
        ^ uVar43 & uVar46
        ^ uVar38
    ) & 0xFFFFFFFF
    uVar43 = (uVar38 ^ ~uVar23) & 0xFFFFFFFF
    uVar20 = (uVar19 & (uVar22 ^ uVar87)) & 0xFFFFFFFF
    uVar43 = (
        (~(uVar43 & uVar48) ^ uVar43 & uVar47 ^ uVar38 ^ uVar23) & uVar51
        ^ (uVar48 ^ ~uVar20 ^ uVar46) & uVar38
        ^ (uVar48 ^ uVar20 ^ uVar46) & uVar23
    ) & 0xFFFFFFFF
    uVar61 = (uVar43 ^ uVar48) & 0xFFFFFFFF
    uVar38 = (
        ((~(uVar47 & (uVar22 ^ uVar87)) ^ uVar46 ^ uVar87) & uVar19 ^ (uVar38 ^ uVar46) & uVar47 ^ uVar38 ^ uVar46) & uVar51
        ^ ((uVar38 ^ uVar20 ^ uVar46) & uVar51 ^ uVar38 ^ uVar20 ^ uVar46) & uVar48
        ^ (uVar38 ^ ~uVar20 ^ uVar46) & uVar23
        ^ uVar38
    ) & 0xFFFFFFFF
    uVar23 = (uVar47 ^ ~uVar51) & 0xFFFFFFFF
    uVar19 = ((~uVar90 ^ uVar60) & uVar72) & 0xFFFFFFFF
    uVar87 = (
        (~((uVar51 ^ uVar47 ^ uVar44) & uVar48) ^ uVar23 & uVar44) & uVar75
        ^ ((uVar51 ^ uVar48 ^ uVar47) & uVar75 ^ uVar51 ^ uVar48 ^ uVar47) & uVar89
        ^ uVar51
    ) & 0xFFFFFFFF
    uVar42 = (
        (~((uVar63 ^ uVar1 ^ uVar90 ^ uVar60) & uVar30) ^ (~uVar1 ^ uVar90 ^ uVar60) & uVar72 ^ uVar1 ^ uVar90 ^ uVar60) & uVar88
        ^ ((uVar63 ^ uVar90 ^ uVar60) & uVar1 ^ uVar72 ^ uVar90 ^ uVar60) & uVar30
        ^ (uVar90 ^ uVar19 ^ uVar60) & uVar1
        ^ uVar90
        ^ uVar19
        ^ uVar60
    ) & 0xFFFFFFFF
    uVar20 = (uVar48 ^ ~uVar51) & 0xFFFFFFFF
    uVar19 = (~(~(_shr(uVar6, 1)) & _shr(uVar2, 1)) & _shr(uVar9, 1)) & 0xFFFFFFFF
    uVar48 = (
        ((uVar23 ^ uVar44) & uVar48 ^ (uVar51 ^ uVar47) & uVar44 ^ uVar47) & uVar75
        ^ (~((uVar47 ^ uVar20) & uVar75) ^ uVar51 ^ uVar48 ^ uVar47) & uVar89
        ^ uVar47 & uVar20
        ^ uVar48
    ) & 0xFFFFFFFF
    uVar15 = (
        (uVar6 << 0x1F & 0xFFFFFFFF) & ~(uVar2 << 0x1F & 0xFFFFFFFF) & ~(uVar9 << 0x1F & 0xFFFFFFFF)
        ^ (uVar9 << 0x1F & 0xFFFFFFFF)
    ) & 0xFFFFFFFF
    uVar8 = ((uVar50 & uVar65 ^ ~uVar31 ^ uVar11) & uVar28 ^ (uVar8 & uVar7 ^ ~uVar27 & uVar50) & uVar65 ^ uVar8) & 0xFFFFFFFF
    uVar22 = (
        (
            (
                ((uVar21 & 0x149601 ^ 0x80A30104) & uVar56 ^ uVar54 & 0x80BF0704 ^ 0x80BE8104) & uVar58
                ^ ((uVar56 ^ 0xFFFEFFFF) & uVar54 & 0xDBABE7FC ^ uVar71) & 0xA4F71907
                ^ 0xDB1FFEFB
            )
            & uVar39
            ^ (
                ((uVar21 & 0x141001 ^ 0x150002) & uVar56 ^ (uVar54 ^ 0xFFFEFFFF) & 0x20490002) & uVar58
                ^ (uVar54 ^ 0x140002) & uVar56 & 0x20550002
                ^ 0xE7FF3945
            )
            & uVar25
            ^ ((uVar21 & 0x148000 ^ 0x80160800) & uVar56 ^ uVar54 & 0xA44A0800 ^ 0xA44A8000) & uVar58
            ^ ((uVar54 ^ 0x140800) & uVar56 & 0xFF573EC1 ^ ~(uVar54 & 0xDF033EC1)) & 0xA4FEC93E
        )
        & uVar64
        ^ (
            ~(((uVar56 ^ 0xFFFF6FFE) & uVar54 ^ 0xFFFFE9FE) & uVar58 & 0x149601) & uVar25 & 0xBCF7DFBF
            ^ (uVar68 ^ 0x1C8000) & uVar58
            ^ 0x111CDEAB
        )
        & uVar39
        ^ (((uVar56 ^ 0x600) & uVar25 & 0x1601 ^ 0xE7FF3947) & uVar54 ^ uVar4 & 0xDBBFFFFF ^ 0xA4FEC13E) & uVar58
        ^ (uVar54 & 0xBCF7DFBF ^ 0x111CDEAB) & uVar56
        ^ (uVar54 ^ uVar25) & 0xDEA23FC5
    ) & 0xFFFFFFFF
    uVar27 = ((uVar35 ^ uVar5) & uVar77) & 0xFFFFFFFF
    uVar54 = ((~uVar27 ^ uVar24 ^ uVar5) & uVar16 ^ (uVar24 ^ uVar27 ^ uVar5) & uVar81 ^ uVar5) & 0xFFFFFFFF
    uVar5 = ((uVar52 ^ uVar81) & (uVar35 ^ uVar5) & uVar77 ^ uVar81 ^ uVar5) & 0xFFFFFFFF
    uVar73 = (((uVar87 ^ uVar14) & (uVar13 ^ uVar41) ^ uVar13 ^ uVar41) & uVar48 ^ uVar14 ^ uVar41) & 0xFFFFFFFF
    uVar50 = (uVar34 ^ ~uVar22) & 0xFFFFFFFF
    uVar27 = (uVar50 & uVar69) & 0xFFFFFFFF
    uVar11 = (
        ~((~((~(uVar50 & uVar40) ^ uVar22 ^ uVar34) & uVar69) ^ ~uVar74 & uVar40 ^ uVar74) & uVar59)
        ^ ~((uVar74 ^ uVar27) & uVar76) & uVar40
        ^ (~uVar27 ^ uVar74 ^ uVar40) & uVar86
        ^ uVar22
    ) & 0xFFFFFFFF
    uVar27 = (~uVar69) & 0xFFFFFFFF
    uVar39 = (
        (~((uVar27 ^ uVar59 ^ uVar76) & uVar40) ^ uVar86 ^ uVar74 ^ uVar69 ^ uVar59) & uVar22
        ^ ~((~uVar22 ^ uVar40) & uVar34) & uVar69
        ^ (uVar86 ^ ~uVar74 ^ uVar69 ^ uVar76) & uVar40
        ^ uVar74
    ) & 0xFFFFFFFF
    uVar21 = ((~uVar59 ^ uVar76) & uVar40) & 0xFFFFFFFF
    uVar50 = (uVar86 ^ uVar21) & 0xFFFFFFFF
    uVar23 = (~((uVar9 & uVar6) << 0x1F & 0xFFFFFFFF) & (uVar2 << 0x1F & 0xFFFFFFFF) ^ 0x7FFFFFFF) & 0xFFFFFFFF
    uVar55 = ((uVar52 ^ uVar24) & uVar81) & 0xFFFFFFFF
    uVar64 = (
        ((uVar34 ^ uVar50 ^ uVar59) & uVar22 ^ (uVar50 ^ uVar59) & uVar34 ^ uVar86 ^ uVar21 ^ uVar59) & uVar69
        ^ (uVar74 & (~uVar59 ^ uVar76) ^ uVar86 ^ uVar22 ^ uVar76) & uVar40
        ^ (uVar86 ^ uVar22 ^ uVar59) & uVar74
        ^ uVar22
    ) & 0xFFFFFFFF
    uVar40 = (~((~uVar88 ^ uVar60) & uVar1)) & 0xFFFFFFFF
    uVar89 = ((uVar37 ^ uVar88 ^ uVar40) & uVar5 ^ (uVar88 ^ uVar40) & uVar37 ^ uVar88) & 0xFFFFFFFF
    uVar26 = (
        ((uVar52 ^ uVar29) & uVar49 ^ uVar16 & uVar29 ^ uVar55) & uVar67
        ^ (~(~uVar24 & uVar16) ^ uVar24) & uVar81
        ^ (uVar16 ^ uVar52 & uVar29) & uVar49
        ^ uVar29
    ) & 0xFFFFFFFF
    uVar43 = (uVar43 << 0x1F & 0xFFFFFFFF) & 0xFFFFFFFF
    uVar43 = (~((uVar38 & uVar85) << 0x1F & 0xFFFFFFFF & ~uVar43) ^ uVar43) & 0xFFFFFFFF
    uVar50 = ((uVar38 ^ uVar85) << 0x1F & 0xFFFFFFFF) & 0xFFFFFFFF
    uVar40 = (~uVar5 ^ uVar37) & 0xFFFFFFFF
    uVar56 = (uVar54 & uVar40) & 0xFFFFFFFF
    uVar20 = (_shr(uVar38, 1)) & 0xFFFFFFFF
    uVar4 = ((~(uVar40 & uVar60) ^ uVar88 & uVar40 ^ uVar5 ^ uVar37) & uVar1 ^ uVar5 ^ uVar88 ^ uVar56) & 0xFFFFFFFF
    uVar72 = (uVar34 ^ uVar69) & 0xFFFFFFFF
    uVar57 = (
        (uVar72 & uVar78 ^ ~(uVar72 & uVar13)) & uVar22 ^ ~((uVar13 ^ uVar78) & uVar69) & uVar34 ^ ~uVar78 & uVar13 & uVar41
    ) & 0xFFFFFFFF
    uVar86 = (~uVar87) & 0xFFFFFFFF
    uVar2 = (~uVar13) & 0xFFFFFFFF
    uVar71 = (
        ~((~((uVar86 ^ uVar13) & uVar14) ^ uVar86 & uVar13 ^ uVar87) & uVar48)
        ^ (~(uVar2 & uVar41) ^ uVar13) & uVar78
        ^ ((uVar13 ^ uVar78) & uVar41 ^ uVar2 & uVar78) & uVar14
        ^ uVar13
        ^ uVar41
    ) & 0xFFFFFFFF
    uVar21 = ((uVar64 ^ uVar11) * 2 & 0xFFFFFFFF) & 0xFFFFFFFF
    uVar40 = (~uVar71) & 0xFFFFFFFF
    uVar51 = (uVar21 ^ 1) & 0xFFFFFFFF
    uVar63 = (uVar73 & uVar40 & 0x7FFFFFFF) & 0xFFFFFFFF
    uVar28 = (
        (
            ((uVar87 ^ uVar41) & uVar48 ^ (uVar2 ^ uVar78) & uVar41 ^ uVar2 & uVar78 ^ uVar13) & uVar14
            ^ (uVar48 & uVar86 ^ uVar13 & uVar78) & uVar41
            ^ uVar13
        )
        & (uVar73 ^ uVar40)
        & 0x7FFFFFFF
    ) & 0xFFFFFFFF
    uVar68 = (~uVar28) & 0xFFFFFFFF
    uVar58 = (
        (uVar38 & uVar61) << 0x1F & 0xFFFFFFFF & ~(uVar85 << 0x1F & 0xFFFFFFFF) ^ (uVar85 << 0x1F & 0xFFFFFFFF)
    ) & 0xFFFFFFFF
    uVar17 = (~(_shr((uVar39 ^ uVar11), 1)) & 0x7FFFFFFF) & 0xFFFFFFFF
    uVar21 = (~((uVar39 * 2 & 0xFFFFFFFF) & ~(uVar64 * 2 & 0xFFFFFFFF)) ^ uVar21) & 0xFFFFFFFF
    uVar92 = (~(_shr(((uVar61 ^ uVar85) & uVar38), 1))) & 0xFFFFFFFF
    uVar90 = (_shr(uVar61, 1) ^ uVar92) & 0xFFFFFFFF
    uVar87 = ((~uVar50 ^ uVar43) & uVar58) & 0xFFFFFFFF
    uVar70 = (
        ~((~((uVar58 ^ uVar50) & uVar43) ^ (~uVar87 ^ uVar43) & uVar36 ^ uVar10) & uVar19)
        ^ (uVar43 ^ uVar87) & uVar10
        ^ (uVar43 ^ ~uVar58) & uVar50
        ^ uVar58
    ) & 0xFFFFFFFF
    uVar61 = (~((uVar67 ^ uVar29 ^ uVar55) & uVar49) ^ (~uVar55 ^ uVar67) & uVar29 ^ uVar16 ^ uVar67) & 0xFFFFFFFF
    uVar71 = (uVar71 ^ uVar73) & 0xFFFFFFFF
    uVar49 = (
        ((uVar67 ^ uVar29 ^ uVar24 ^ uVar49) & uVar16 ^ (uVar67 ^ uVar29 ^ uVar49) & uVar24 ^ uVar67 ^ uVar29 ^ uVar49) & uVar81
        ^ ((uVar16 ^ uVar29) & uVar49 ^ uVar52 & uVar29) & uVar67
        ^ (uVar52 & uVar49 ^ uVar16) & uVar29
        ^ uVar49
    ) & 0xFFFFFFFF
    uVar38 = (uVar71 & 0x7FFFFFFF) & 0xFFFFFFFF
    uVar16 = (~uVar39 & uVar64 & uVar11 & 0xFFFFFFFD) & 0xFFFFFFFF
    uVar55 = (~(uVar11 << 0x1F & 0xFFFFFFFF) & (uVar39 << 0x1F & 0xFFFFFFFF)) & 0xFFFFFFFF
    uVar52 = ((uVar64 ^ uVar11) << 0x1F & 0xFFFFFFFF ^ uVar55) & 0xFFFFFFFF
    uVar87 = (~uVar34 ^ uVar69) & 0xFFFFFFFF
    uVar40 = (
        (~((uVar87 ^ uVar13 ^ uVar41) & uVar78) ^ uVar87 & uVar13 ^ uVar34 ^ uVar41) & uVar22
        ^ (~((~uVar34 ^ uVar13) & uVar78) ^ uVar34 ^ uVar13) & uVar41
        ^ ((uVar27 ^ uVar13) & uVar34 ^ uVar13) & uVar78
        ^ ~(uVar27 & uVar13) & uVar34
    ) & 0xFFFFFFFF
    uVar14 = (
        ~(~((uVar11 * 2 & 0xFFFFFFFF) & ~(uVar64 * 2 & 0xFFFFFFFF)) & (uVar39 * 2 & 0xFFFFFFFF)) ^ (uVar11 * 2 & 0xFFFFFFFF)
    ) & 0xFFFFFFFF
    uVar55 = ((uVar64 << 0x1F & 0xFFFFFFFF) ^ uVar55) & 0xFFFFFFFF
    uVar73 = (~((uVar64 & uVar11) << 0x1F & 0xFFFFFFFF) ^ (uVar39 << 0x1F & 0xFFFFFFFF)) & 0xFFFFFFFF
    uVar92 = (_shr(uVar85, 1) ^ uVar92) & 0xFFFFFFFF
    uVar74 = (_shr(uVar11, 1)) & 0xFFFFFFFF
    uVar29 = (_shr(uVar64, 1)) & 0xFFFFFFFF
    uVar87 = ((~uVar74 & _shr(uVar39, 1) ^ uVar74) & uVar29) & 0xFFFFFFFF
    uVar85 = (~uVar87) & 0xFFFFFFFF
    uVar9 = (uVar68 & (~uVar90 ^ uVar20)) & 0xFFFFFFFF
    uVar6 = (~uVar9) & 0xFFFFFFFF
    uVar86 = (uVar63 & (~uVar90 ^ uVar20)) & 0xFFFFFFFF
    uVar27 = (~uVar86 ^ uVar90 ^ uVar20) & 0xFFFFFFFF
    uVar7 = (uVar68 & uVar27) & 0xFFFFFFFF
    uVar24 = (~uVar63) & 0xFFFFFFFF
    uVar25 = (uVar24 & uVar90) & 0xFFFFFFFF
    uVar7 = (
        ~((~((uVar90 ^ uVar20 ^ uVar6) & uVar38) ^ uVar90 ^ uVar20 ^ uVar7 ^ uVar86) & uVar92)
        ^ (~((uVar25 ^ uVar63) & uVar20) ^ uVar90 ^ uVar9) & uVar38
        ^ (uVar90 ^ uVar20) & uVar63
        ^ uVar90
        ^ uVar7
    ) & 0xFFFFFFFF
    uVar64 = ((uVar64 ^ uVar39) & uVar11 & 0xFFFFFFFD ^ 2) & 0xFFFFFFFF
    uVar74 = ((~uVar29 & _shr(uVar39, 1) ^ uVar29) & uVar74 ^ 0x80000000) & 0xFFFFFFFF
    uVar5 = (
        ((uVar37 ^ uVar60) & uVar1 ^ uVar5 ^ uVar37 ^ uVar56) & uVar88 ^ (~uVar54 & uVar5 ^ uVar53) & uVar37 ^ uVar5
    ) & 0xFFFFFFFF
    uVar78 = (
        ((uVar69 ^ uVar13) & uVar78 ^ uVar2 & uVar69) & uVar34
        ^ ((uVar72 ^ uVar13 ^ uVar41) & uVar78 ^ uVar72 & uVar13 ^ uVar69 ^ uVar41) & uVar22
        ^ ((uVar34 ^ uVar13) & uVar78 ^ uVar34 ^ uVar13) & uVar41
        ^ uVar13
        ^ uVar78
    ) & 0xFFFFFFFF
    uVar1 = (
        (
            ~((~((uVar19 ^ uVar36) & uVar43) ^ uVar58 ^ uVar19 ^ uVar36) & uVar50)
            ^ ((~uVar19 ^ uVar36) & uVar58 ^ uVar19 ^ uVar36) & uVar43
            ^ uVar58
            ^ uVar19
        )
        & uVar10
        ^ ((uVar50 ^ ~uVar58) & uVar43 ^ 0xFFFFFFFF ^ uVar50) & uVar19
        ^ (~uVar43 & uVar58 ^ uVar43) & uVar50
        ^ uVar58
    ) & 0xFFFFFFFF
    uVar41 = ((~uVar23 ^ uVar15) & uVar12) & 0xFFFFFFFF
    uVar43 = (
        ~((~((uVar50 ^ uVar43) & uVar36) ^ uVar10) & uVar19)
        ^ (~uVar43 & uVar58 ^ uVar10) & uVar50
        ^ (uVar43 ^ uVar36) & uVar10
        ^ uVar58
        ^ uVar43
    ) & 0xFFFFFFFF
    uVar87 = (uVar87 & uVar74) & 0xFFFFFFFF
    uVar50 = (~uVar41) & 0xFFFFFFFF
    uVar9 = ((uVar87 ^ uVar50 ^ uVar23) & uVar17 ^ (uVar85 ^ uVar41 ^ uVar23) & uVar74 ^ uVar23 ^ uVar15) & 0xFFFFFFFF
    uVar10 = (~uVar1 ^ uVar70) & 0xFFFFFFFF
    uVar36 = (~uVar70) & 0xFFFFFFFF
    uVar67 = (~uVar49 ^ uVar26) & 0xFFFFFFFF
    uVar44 = (
        ((~(uVar36 & uVar49) ^ uVar70) & uVar1 ^ uVar49) & uVar26
        ^ (~((uVar1 ^ ~(uVar10 & uVar49) ^ uVar70) & uVar26) ^ uVar1 ^ uVar70) & uVar43
        ^ uVar67 & uVar61
        ^ uVar1 & uVar36
        ^ uVar49
    ) & 0xFFFFFFFF
    uVar19 = ((~uVar38 ^ uVar63) & uVar68) & 0xFFFFFFFF
    uVar41 = ((uVar39 ^ uVar11) & 0xFFFFFFFD) & 0xFFFFFFFF
    uVar27 = (
        ((uVar19 ^ uVar38 ^ uVar63) & uVar20 ^ uVar38 & uVar24 ^ uVar63) & uVar90
        ^ (~((uVar28 ^ uVar63) & uVar38) ^ uVar24 & uVar68 ^ uVar63) & uVar20
        ^ ~(uVar92 & uVar27) & uVar38
    ) & 0xFFFFFFFF
    uVar72 = (~uVar74) & 0xFFFFFFFF
    uVar46 = (
        ~((~((uVar74 ^ uVar85 ^ uVar12) & uVar23) ^ (uVar85 ^ uVar72 ^ uVar12) & uVar15 ^ uVar85 & uVar72 ^ uVar12) & uVar17)
        ^ (uVar85 ^ uVar23 ^ uVar12) & uVar15
        ^ (uVar85 ^ uVar50 ^ uVar23) & uVar74
        ^ (uVar85 ^ uVar12) & uVar23
        ^ uVar85
        ^ uVar12
    ) & 0xFFFFFFFF
    uVar24 = (uVar27 * 2 & 0xFFFFFFFF) & 0xFFFFFFFF
    uVar86 = (uVar7 * 2 & 0xFFFFFFFF) & 0xFFFFFFFF
    uVar37 = (~uVar24 ^ uVar86) & 0xFFFFFFFF
    uVar39 = (uVar78 ^ uVar57 ^ uVar66) & 0xFFFFFFFF
    uVar50 = ((uVar33 ^ uVar45) & uVar66) & 0xFFFFFFFF
    uVar31 = (
        ((uVar78 ^ uVar57) & uVar66 ^ uVar40 & uVar39 ^ uVar57) & uVar45
        ^ (~uVar78 ^ uVar40 ^ uVar57 ^ uVar45) & uVar33 & uVar66
        ^ (~uVar40 ^ uVar57) & uVar78
        ^ uVar57
    ) & 0xFFFFFFFF
    uVar11 = ((~uVar50 ^ uVar78 ^ uVar40) & uVar57 ^ (uVar40 ^ uVar50) & uVar78 ^ uVar40 ^ uVar45) & 0xFFFFFFFF
    uVar54 = (~uVar5 ^ uVar4) & 0xFFFFFFFF
    uVar56 = (uVar54 & uVar89) & 0xFFFFFFFF
    uVar53 = ((uVar56 ^ uVar4) & uVar1) & 0xFFFFFFFF
    uVar56 = (~uVar56) & 0xFFFFFFFF
    uVar13 = (~((uVar1 ^ uVar56 ^ uVar4) & uVar43) ^ uVar53) & 0xFFFFFFFF
    uVar12 = ((~uVar15 ^ uVar12) & uVar23 ^ (uVar92 ^ uVar20) & uVar90 ^ uVar20 ^ uVar12) & 0xFFFFFFFF
    uVar72 = (
        (~((uVar52 ^ uVar72) & uVar55) ^ uVar74 ^ uVar52) & uVar73 ^ ~((uVar85 ^ uVar55 ^ uVar17) & uVar52) & uVar74 ^ uVar17
    ) & 0xFFFFFFFF
    uVar50 = ((~(~uVar32 & uVar3) ^ uVar12 ^ uVar32) & uVar8 ^ uVar12 & uVar3) & 0xFFFFFFFF
    uVar2 = (
        ((uVar85 ^ uVar52) & uVar74 ^ (uVar73 ^ uVar52) & uVar55 ^ uVar73 ^ uVar52) & uVar17
        ^ (~uVar73 & uVar55 ^ uVar73 ^ uVar87) & uVar52
        ^ uVar74
    ) & 0xFFFFFFFF
    uVar58 = ((uVar16 ^ uVar41 ^ uVar14 ^ uVar51) & uVar64 & uVar21 ^ uVar41 ^ uVar14) & 0xFFFFFFFF
    uVar22 = (~uVar12 & uVar3) & 0xFFFFFFFF
    uVar87 = (
        (
            ~(
                (
                    ~(
                        ((~(~uVar20 & uVar68) ^ uVar20) & uVar90 ^ (~uVar20 & uVar90 ^ uVar20 ^ uVar6) & uVar92 ^ uVar68 ^ uVar20)
                        & uVar38
                    )
                    ^ (~(uVar92 & uVar28 & uVar90) ^ uVar68) & uVar20
                    ^ uVar90
                )
                & uVar63
            )
            ^ (~(~(~uVar38 & uVar68) & uVar92) & uVar90 ^ uVar28 & uVar38 ^ uVar68) & uVar20
            ^ uVar38
            ^ uVar90
        )
        * 2
        & 0xFFFFFFFF
    ) & 0xFFFFFFFF
    uVar34 = ((~((~uVar22 ^ uVar12) & uVar8) ^ uVar12 ^ uVar22) & uVar32 ^ (~uVar8 ^ uVar3) & uVar12) & 0xFFFFFFFF
    uVar86 = (~(~(~uVar86 & uVar24) & uVar87) ^ uVar86) & 0xFFFFFFFF
    uVar24 = (~((uVar27 & uVar7) * 2 & 0xFFFFFFFF) & uVar87 ^ uVar24) & 0xFFFFFFFF
    uVar52 = (
        ~((~((~uVar52 ^ uVar17) & uVar55) ^ uVar52 ^ uVar17) & uVar73) ^ (~uVar52 ^ uVar17) & uVar74 & uVar85 ^ uVar74 ^ uVar52
    ) & 0xFFFFFFFF
    uVar57 = (
        (uVar39 & uVar45 ^ uVar33 & uVar66 ^ uVar57) & uVar40 ^ (~uVar33 & uVar66 ^ uVar78) & uVar45 ^ uVar78 ^ uVar57
    ) & 0xFFFFFFFF
    uVar55 = ((uVar18 ^ uVar84) & uVar42) & 0xFFFFFFFF
    uVar47 = (~uVar72) & 0xFFFFFFFF
    uVar28 = (uVar18 & uVar84) & 0xFFFFFFFF
    uVar73 = (~uVar42 & uVar18 & uVar84) & 0xFFFFFFFF
    uVar22 = (~uVar55 ^ uVar28) & 0xFFFFFFFF
    uVar45 = (~uVar18) & 0xFFFFFFFF
    uVar87 = (
        ((~((~uVar2 & uVar72 ^ uVar2) & uVar18) ^ uVar72) & uVar84 ^ (uVar45 ^ uVar2) & uVar72 ^ uVar18 ^ uVar2) & uVar42
        ^ (uVar22 & uVar72 ^ uVar73 ^ uVar42) & uVar52 & uVar2
        ^ ~(uVar47 & uVar2) & uVar18 & uVar84
        ^ uVar72
    ) & 0xFFFFFFFF
    uVar6 = (
        ((uVar45 ^ uVar84 ^ uVar2) & uVar42 ^ uVar28 ^ uVar2) & uVar72
        ^ ~((uVar47 ^ uVar42) & uVar52) & uVar2
        ^ (uVar28 ^ uVar2) & uVar42
        ^ uVar28
    ) & 0xFFFFFFFF
    uVar66 = (~uVar41) & 0xFFFFFFFF
    uVar40 = ((uVar66 ^ uVar51) & uVar14) & 0xFFFFFFFF
    uVar27 = (
        ~(((uVar66 ^ uVar14 ^ uVar21) & uVar16 ^ (uVar66 ^ uVar21) & uVar14 ^ (uVar41 ^ uVar51) & uVar21 ^ uVar41) & uVar64)
        ^ (uVar66 & uVar51 ^ uVar40 ^ uVar41) & uVar21
    ) & 0xFFFFFFFF
    uVar14 = (
        (~uVar14 & uVar41 ^ ~(uVar16 & (uVar41 ^ uVar14))) & uVar64 ^ (uVar41 & uVar51 ^ ~uVar40) & uVar21 ^ uVar41 ^ uVar14
    ) & 0xFFFFFFFF
    uVar88 = (
        (
            (
                ~((~((uVar47 ^ uVar18) & uVar52) ^ uVar45 & uVar72 ^ uVar18) & uVar84)
                ^ (~(uVar47 & uVar52) ^ uVar72) & uVar18
                ^ uVar72
                ^ uVar52
            )
            & uVar42
            ^ ~uVar28 & uVar72 & uVar52
        )
        & uVar2
        ^ (uVar73 ^ uVar42) & uVar72
        ^ uVar42
    ) & 0xFFFFFFFF
    uVar40 = (~(uVar14 << 2 & 0xFFFFFFFF) & (uVar27 << 2 & 0xFFFFFFFF) ^ (uVar58 << 2 & 0xFFFFFFFF) ^ 3) & 0xFFFFFFFF
    uVar66 = (uVar1 ^ ~uVar43) & 0xFFFFFFFF
    uVar21 = (
        ~(((uVar5 & uVar66 ^ ~(uVar4 & uVar66) ^ uVar43 ^ uVar1) & uVar89 ^ uVar4 & uVar66) & uVar70) ^ ~uVar53 & uVar43 ^ uVar1
    ) & 0xFFFFFFFF
    uVar7 = (
        (~((~(uVar43 & uVar54) ^ uVar5 ^ uVar4) & uVar1) ^ uVar5 ^ uVar4) & uVar89
        ^ ~(uVar1 & ~uVar43) & uVar4
        ^ uVar70 & uVar66
        ^ uVar1
    ) & 0xFFFFFFFF
    uVar66 = ((uVar74 ^ uVar85) & uVar17) & 0xFFFFFFFF
    uVar17 = (
        ~((uVar74 ^ uVar85 ^ uVar23 ^ uVar66) & uVar15) ^ (~uVar66 ^ uVar74 ^ uVar85) & uVar23 ^ uVar74 ^ uVar17
    ) & 0xFFFFFFFF
    uVar51 = (~(uVar58 << 2 & 0xFFFFFFFF) & (uVar27 << 2 & 0xFFFFFFFF) ^ (uVar14 ^ uVar58) << 2 & 0xFFFFFFFF) & 0xFFFFFFFF
    uVar75 = (((~uVar32 & uVar3 ^ uVar32) & uVar12 ^ uVar3) & uVar8 ^ (~uVar12 ^ uVar32) & uVar3 ^ uVar12 ^ uVar32) & 0xFFFFFFFF
    uVar73 = ((uVar58 ^ uVar14 & uVar27) << 2 & 0xFFFFFFFF) & 0xFFFFFFFF
    uVar41 = (uVar14 & uVar27 & 0xFFFFFFF3 ^ 0xC) & 0xFFFFFFFF
    uVar45 = (~uVar31 ^ uVar57) & 0xFFFFFFFF
    uVar64 = (uVar46 & uVar45 ^ uVar31 ^ uVar57 ^ ~(uVar17 & uVar45)) & 0xFFFFFFFF
    uVar23 = (uVar17 ^ ~uVar46) & 0xFFFFFFFF
    uVar74 = ((~(uVar14 & uVar58) ^ uVar27 & (uVar14 ^ uVar58)) & 0xFFFFFFF3) & 0xFFFFFFFF
    uVar66 = (~(uVar57 & uVar23) ^ uVar46 ^ uVar17) & 0xFFFFFFFF
    uVar27 = ((uVar14 ^ uVar27) & 0xFFFFFFF3) & 0xFFFFFFFF
    uVar33 = ((~(uVar11 & uVar64) ^ uVar31 & uVar66 ^ uVar46 ^ uVar17) & uVar9 ^ uVar46 ^ uVar17) & 0xFFFFFFFF
    uVar85 = (
        ((~uVar74 ^ uVar41 ^ uVar73 ^ uVar51) & uVar40 ^ uVar41 ^ uVar73 ^ uVar51) & uVar27
        ^ (~uVar41 ^ uVar73 ^ uVar51) & uVar40
        ^ uVar41
        ^ uVar73
    ) & 0xFFFFFFFF
    uVar35 = (
        (uVar70 & (uVar49 ^ uVar26) ^ uVar49 ^ uVar26) & uVar1 ^ uVar43 & uVar10 & (uVar49 ^ uVar26) ^ ~uVar26 & uVar49
    ) & 0xFFFFFFFF
    uVar14 = (
        ~((~(uVar9 & uVar64) ^ uVar31 ^ uVar57) & uVar11) ^ (~(uVar9 & uVar66) ^ uVar57) & uVar31 ^ uVar17 & ~uVar46
    ) & 0xFFFFFFFF
    uVar64 = (
        ~(((uVar40 ^ uVar74 ^ uVar41) & uVar51 ^ uVar74 ^ ~uVar40 & uVar73) & uVar27)
        ^ (~(~uVar40 & uVar73) ^ uVar41 ^ uVar40) & uVar51
        ^ uVar40
    ) & 0xFFFFFFFF
    uVar74 = (uVar27 & (uVar74 ^ uVar41)) & 0xFFFFFFFF
    uVar66 = (
        ~(
            (
                ~((uVar10 & uVar26 ^ uVar1 ^ ~(uVar10 & uVar49) ^ uVar70) & uVar43)
                ^ (~(uVar67 & uVar70) ^ uVar49 ^ uVar26) & uVar1
                ^ uVar49
                ^ uVar26
            )
            & uVar61
        )
        ^ uVar49
        ^ uVar26
    ) & 0xFFFFFFFF
    uVar27 = ((uVar73 & uVar51 ^ ~uVar74 ^ uVar41) & uVar40 ^ (uVar41 ^ uVar73 ^ uVar74) & uVar51 ^ uVar27) & 0xFFFFFFFF
    uVar39 = (uVar27 & uVar85) & 0xFFFFFFFF
    uVar62 = (
        ((~(~uVar17 & uVar57) ^ uVar17) & uVar31 ^ ~((uVar31 ^ uVar57 ^ ~(uVar17 & uVar45)) & uVar11)) & uVar46 ^ uVar17
    ) & 0xFFFFFFFF
    uVar73 = ((uVar27 ^ uVar85) & 0xFFFFFF0F) & 0xFFFFFFFF
    uVar41 = (~(uVar85 << 4 & 0xFFFFFFFF) & (uVar27 << 4 & 0xFFFFFFFF) ^ (uVar64 & uVar85) << 4 & 0xFFFFFFFF) & 0xFFFFFFFF
    uVar40 = (~(uVar27 << 4 & 0xFFFFFFFF) & (uVar85 << 4 & 0xFFFFFFFF) ^ (uVar64 << 4 & 0xFFFFFFFF)) & 0xFFFFFFFF
    uVar51 = (~(uVar39 & 0xFFFFFF0F)) & 0xFFFFFFFF
    uVar54 = (~(uVar39 << 4 & 0xFFFFFFFF) ^ (uVar64 << 4 & 0xFFFFFFFF)) & 0xFFFFFFFF
    uVar85 = ((uVar64 & (uVar27 ^ uVar85) ^ uVar39) & 0xFFFFFF0F) & 0xFFFFFFFF
    uVar27 = (
        ((uVar40 ^ uVar73) & uVar41 ^ uVar40 ^ uVar73) & uVar51
        ^ (uVar40 & (uVar41 ^ uVar51) ^ uVar41 ^ uVar51) & uVar54
        ^ ~(uVar85 & (uVar41 ^ uVar51)) & uVar73
        ^ uVar41
    ) & 0xFFFFFFFF
    uVar74 = (
        (~((uVar40 ^ uVar51 ^ uVar85) & uVar41) ^ uVar40 ^ uVar51 ^ uVar85) & uVar73
        ^ ((uVar41 ^ uVar73) & uVar40 ^ uVar41 ^ uVar73) & uVar54
        ^ uVar51
    ) & 0xFFFFFFFF
    uVar54 = (
        (uVar54 & (uVar39 & 0xFFFFFF0F ^ uVar73) ^ 0xFFFFFFFF ^ uVar51 ^ uVar73) & uVar40
        ^ (uVar85 & uVar73 ^ uVar41 ^ uVar54) & uVar51
        ^ (~uVar41 ^ uVar54) & uVar73
        ^ uVar54
    ) & 0xFFFFFFFF
    uVar64 = (~(~(uVar54 << 8 & 0xFFFFFFFF) & (uVar74 << 8 & 0xFFFFFFFF)) ^ (uVar54 ^ uVar27) << 8 & 0xFFFFFFFF) & 0xFFFFFFFF
    uVar40 = ((uVar74 & uVar27 ^ uVar54) << 8 & 0xFFFFFFFF) & 0xFFFFFFFF
    uVar41 = (~(uVar27 << 8 & 0xFFFFFFFF) & (uVar74 << 8 & 0xFFFFFFFF) ^ (uVar54 << 8 & 0xFFFFFFFF)) & 0xFFFFFFFF
    uVar73 = ((~uVar27 & uVar74 ^ uVar54) & 0xFFFF00FF) & 0xFFFFFFFF
    uVar51 = ((~uVar54 & uVar27 ^ uVar74) & 0xFFFF00FF) & 0xFFFFFFFF
    uVar74 = (((uVar54 ^ uVar74) & uVar27 ^ uVar54) & 0xFFFF00FF) & 0xFFFFFFFF
    uVar85 = (~uVar41 ^ uVar64) & 0xFFFFFFFF
    uVar27 = ((~(uVar51 & uVar85) ^ uVar73 & uVar85 ^ uVar41 ^ uVar64) & uVar40 ^ uVar51 ^ uVar41) & 0xFFFFFFFF
    uVar64 = (
        ~((~((uVar74 ^ uVar41) & uVar73) ^ ~uVar74 & uVar41) & uVar51)
        ^ (~((uVar74 ^ uVar40) & uVar41) ^ uVar74 ^ uVar40) & uVar73
        ^ (uVar73 ^ uVar41) & uVar40 & uVar64
    ) & 0xFFFFFFFF
    uVar41 = (
        ~((~(uVar40 & uVar85) ^ uVar74 ^ uVar41) & uVar51) ^ (uVar74 ^ uVar41 ^ uVar40 & uVar85) & uVar73 ^ uVar41
    ) & 0xFFFFFFFF
    uVar10 = ((uVar64 ^ uVar27) & 0xFFFF) & 0xFFFFFFFF
    uVar85 = (uVar64 & uVar27 & 0xFFFF) & 0xFFFFFFFF
    uVar40 = (uVar41 << 0x10 & 0xFFFFFFFF) & 0xFFFFFFFF
    uVar51 = ((uVar41 ^ uVar64) << 0x10 & 0xFFFFFFFF) & 0xFFFFFFFF
    uVar73 = ((uVar41 & (uVar64 ^ uVar27) ^ uVar27) & 0xFFFF) & 0xFFFFFFFF
    uVar41 = (~(~(uVar27 << 0x10 & 0xFFFFFFFF) & (uVar64 << 0x10 & 0xFFFFFFFF)) ^ uVar40) & 0xFFFFFFFF
    uVar40 = (~(~(~uVar40 & (uVar64 << 0x10 & 0xFFFFFFFF)) & (uVar27 << 0x10 & 0xFFFFFFFF)) ^ uVar40) & 0xFFFFFFFF
    uVar29 = (
        ~((uVar51 & (~uVar40 ^ uVar85) ^ uVar40 & uVar85) & uVar41)
        ^ (uVar10 & (~uVar40 ^ uVar85) ^ uVar40 & uVar85) & uVar73
        ^ uVar85
        ^ uVar10
    ) & 0xFFFFFFFF
    uVar48 = (
        ((~uVar51 ^ uVar85) & uVar41 ^ uVar73 & (uVar85 ^ uVar10) ^ uVar85 ^ uVar10) & uVar40
        ^ (~uVar10 & uVar73 ^ uVar41 & uVar51 ^ uVar10) & uVar85
        ^ uVar10
    ) & 0xFFFFFFFF
    uVar10 = (((uVar40 ^ uVar51) & (uVar85 ^ uVar10) ^ uVar40 ^ uVar51) & uVar41 ^ uVar40 ^ uVar10) & 0xFFFFFFFF
    uVar78 = ((uVar56 ^ uVar4) & uVar10) & 0xFFFFFFFF
    uVar30 = ((uVar5 ^ uVar4 ^ uVar78) & uVar29 ^ (uVar5 ^ uVar56) & uVar10 ^ uVar5 ^ uVar4) & 0xFFFFFFFF
    uVar85 = (~uVar10) & 0xFFFFFFFF
    uVar58 = (uVar29 ^ uVar85) & 0xFFFFFFFF
    uVar41 = (uVar48 & uVar58) & 0xFFFFFFFF
    uVar51 = (uVar10 ^ uVar41) & 0xFFFFFFFF
    uVar15 = ((uVar11 & uVar51 ^ uVar10 ^ uVar29) & uVar57 ^ (uVar29 ^ uVar41) & uVar11 ^ uVar10 ^ uVar29) & 0xFFFFFFFF
    uVar76 = (~uVar29) & 0xFFFFFFFF
    uVar16 = (((~(uVar48 & 0xFFFFFFE9) ^ uVar29 & 0x16) & uVar10 ^ uVar48 & uVar76 & 0xFFFFFFE9) & 0x7FFFFFFF) & 0xFFFFFFFF
    uVar73 = (((uVar10 ^ uVar48) & uVar12 ^ uVar10 ^ uVar48) & uVar29 ^ uVar10 ^ uVar48) & 0xFFFFFFFF
    uVar59 = (uVar48 ^ uVar29) & 0xFFFFFFFF
    uVar77 = (
        ((uVar59 & uVar57 ^ uVar48 ^ uVar29) & uVar31 ^ (uVar31 & uVar59 ^ uVar29 ^ uVar76 & uVar57) & uVar11 ^ uVar57) & uVar10
        ^ (~((~uVar11 ^ uVar57) & uVar29) ^ uVar11 ^ uVar57) & uVar31 & uVar48
        ^ (uVar11 ^ uVar57) & uVar29
        ^ uVar11
        ^ uVar57
    ) & 0xFFFFFFFF
    uVar64 = (~uVar1 & uVar70) & 0xFFFFFFFF
    uVar74 = (uVar29 & (~uVar64 ^ uVar1)) & 0xFFFFFFFF
    uVar40 = (
        ((~(uVar70 & uVar51) ^ uVar10 ^ uVar41) & uVar1 ^ (uVar36 & uVar29 ^ uVar70 ^ uVar10) & uVar48 ^ uVar10) & uVar43
        ^ (~uVar74 ^ uVar64) & uVar48
        ^ uVar1
    ) & 0xFFFFFFFF
    uVar39 = (~((~(uVar5 & uVar51) ^ uVar10 ^ uVar29) & uVar4) ^ (~uVar41 ^ uVar29) & uVar5 ^ uVar10 ^ uVar29) & 0xFFFFFFFF
    uVar57 = (
        (~((~(uVar58 & uVar57) ^ uVar10 ^ uVar29) & uVar48) ^ (uVar29 & uVar45 ^ uVar31) & uVar10) & uVar11
        ^ (~(uVar76 & uVar57) ^ uVar29) & uVar31 & uVar10
        ^ uVar57
    ) & 0xFFFFFFFF
    uVar54 = (~uVar48) & 0xFFFFFFFF
    uVar56 = (uVar54 & uVar10) & 0xFFFFFFFF
    uVar41 = (
        ((~(uVar54 & uVar17) ^ uVar48) & uVar10 ^ (uVar51 & uVar17 ^ uVar56) & uVar46) & uVar9
        ^ ~((~(uVar46 & uVar76) ^ uVar10) & uVar48) & uVar17
        ^ uVar10
    ) & 0xFFFFFFFF
    uVar27 = (
        (~((uVar8 & uVar54 ^ uVar48) & uVar3) ^ uVar48) & uVar10 ^ ((~(uVar3 & uVar76) ^ uVar29) & uVar32 ^ uVar3) & uVar48
    ) & 0xFFFFFFFF
    uVar45 = ((uVar10 & 0x7FFFFFFF ^ uVar48) & uVar29 ^ (uVar48 ^ 0x80000000) & uVar10 ^ uVar48) & 0xFFFFFFFF
    uVar11 = (uVar5 & uVar58) & 0xFFFFFFFF
    uVar53 = (
        ~((~((~(uVar29 & uVar23) ^ uVar46 ^ uVar17) & uVar9) ^ (~(uVar46 & uVar76) ^ uVar29) & uVar17 ^ uVar29) & uVar10 & uVar48)
        ^ uVar48
        ^ uVar17
    ) & 0xFFFFFFFF
    uVar31 = (
        (
            ~((~(uVar4 & uVar58) ^ uVar11 ^ uVar10 ^ uVar29) & uVar89)
            ^ (~uVar11 ^ uVar10 ^ uVar29) & uVar4
            ^ uVar11
            ^ uVar10
            ^ uVar29
        )
        & uVar48
        ^ (~uVar78 ^ uVar5 ^ uVar4) & uVar29
        ^ ~(~uVar5 & uVar4) & uVar10
    ) & 0xFFFFFFFF
    uVar17 = (
        ~(
            (
                (~((~(uVar10 & uVar23) ^ uVar46 ^ uVar17) & uVar29) ^ uVar46 ^ uVar17) & uVar9
                ^ (~((~(uVar46 & uVar85) ^ uVar10) & uVar17) ^ uVar10) & uVar29
                ^ uVar46 & uVar17
                ^ uVar10
            )
            & uVar48
        )
        ^ ((uVar9 ^ uVar17) & uVar46 ^ uVar9 & ~uVar17) & uVar10
        ^ uVar17
    ) & 0xFFFFFFFF
    uVar5 = (~uVar8 ^ uVar32) & 0xFFFFFFFF
    uVar4 = (
        (~(((~(uVar5 & uVar10) ^ uVar8 ^ uVar32) & uVar29 ^ uVar8 ^ uVar32) & uVar3) ^ ~(uVar29 & uVar85) & uVar32 ^ uVar10)
        & uVar48
        ^ (~((uVar8 ^ uVar32) & uVar3) ^ uVar32) & uVar10
        ^ uVar3
    ) & 0xFFFFFFFF
    uVar9 = (uVar57 ^ uVar14 ^ uVar33) & 0xFFFFFFFF
    uVar46 = (uVar14 ^ uVar33) & 0xFFFFFFFF
    uVar65 = (
        ((~uVar15 ^ uVar14 ^ uVar33) & uVar57 ^ ~(uVar77 & uVar9) ^ uVar46 & uVar15 ^ uVar14) & uVar62
        ^ (~uVar57 ^ uVar77 ^ uVar15) & uVar14
        ^ uVar15
    ) & 0xFFFFFFFF
    uVar3 = (~(~(((~(uVar5 & uVar29) ^ uVar8 ^ uVar32) & uVar3 ^ uVar32 & uVar76) & uVar48) & uVar10) ^ uVar3) & 0xFFFFFFFF
    uVar79 = (
        ((~uVar27 ^ uVar34) & uVar75 ^ (uVar4 ^ uVar27) & uVar3 ^ uVar4) & uVar50
        ^ (~uVar3 & uVar4 ^ uVar75 & uVar34 ^ uVar3) & uVar27
        ^ uVar3
        ^ uVar34
    ) & 0xFFFFFFFF
    uVar23 = (~(~(uVar12 & uVar59) & uVar10) ^ uVar48) & 0xFFFFFFFF
    uVar60 = (~((uVar10 & 0x16 ^ uVar54) & uVar29 & 0x7FFFFFFF) ^ ((uVar48 ^ 0x16) & uVar10 ^ uVar48) & 0x7FFFFFFF) & 0xFFFFFFFF
    uVar8 = (~uVar60) & 0xFFFFFFFF
    uVar78 = ((uVar60 ^ ~(uVar8 & uVar26)) & uVar49) & 0xFFFFFFFF
    uVar59 = (
        ~((~(((~(uVar60 & uVar67) ^ uVar49 ^ uVar26) & uVar61 ^ uVar60 ^ uVar78) & uVar45) ^ uVar61) & uVar16) ^ uVar45 & uVar61
    ) & 0xFFFFFFFF
    uVar12 = ((~(uVar12 & uVar48 & uVar85) ^ uVar10 ^ uVar48) & uVar29 ^ uVar12) & 0xFFFFFFFF
    uVar5 = ((uVar8 ^ uVar16) & uVar45) & 0xFFFFFFFF
    uVar85 = (uVar5 ^ uVar16) & 0xFFFFFFFF
    uVar67 = (
        ~((~((~(uVar1 & uVar85) ^ uVar45 & uVar8) & uVar70) ^ (uVar1 & uVar8 ^ uVar60) & uVar45) & uVar43)
        ^ (~((~(uVar8 & uVar70) ^ uVar60) & uVar1) ^ uVar70) & uVar45
        ^ uVar70
    ) & 0xFFFFFFFF
    uVar11 = (
        ((~((uVar1 & uVar58 ^ uVar10) & uVar70) ^ uVar1 & uVar58 ^ uVar10 ^ uVar29) & uVar48 ^ uVar10 & (~uVar64 ^ uVar1))
        & uVar43
        ^ (~((~(uVar1 & uVar54) ^ uVar48) & uVar70) ^ uVar1 & uVar54 ^ uVar48) & uVar10
        ^ uVar1
        ^ uVar48
    ) & 0xFFFFFFFF
    uVar32 = (~uVar45) & 0xFFFFFFFF
    uVar58 = ((~uVar78 ^ uVar60) & uVar45) & 0xFFFFFFFF
    uVar22 = (~((~(uVar22 & uVar45) ^ uVar18) & uVar16) ^ uVar45 & uVar18) & 0xFFFFFFFF
    uVar78 = (((~(uVar32 & uVar49) ^ uVar45) & uVar26 & uVar16 ^ ~uVar58) & uVar61 ^ uVar58 ^ uVar16) & 0xFFFFFFFF
    uVar58 = (~uVar31) & 0xFFFFFFFF
    uVar69 = (~uVar7 ^ uVar21) & 0xFFFFFFFF
    uVar89 = (
        (~((uVar58 ^ uVar21) & uVar39) ^ (uVar58 ^ uVar7) & uVar21 ^ uVar13 & uVar69 ^ uVar7) & uVar30
        ^ (~(~uVar39 & uVar31) ^ uVar13 & uVar7) & uVar21
        ^ uVar31
    ) & 0xFFFFFFFF
    uVar26 = (
        ((uVar85 & uVar26 ^ uVar32 & uVar16) & uVar49 ^ (~(uVar8 & uVar26) ^ uVar16) & uVar45) & uVar61
        ^ ~((~(uVar32 & uVar26) ^ uVar45) & uVar49) & uVar16
        ^ uVar45
    ) & 0xFFFFFFFF
    uVar61 = (((~uVar5 ^ uVar16) & uVar70 ^ (uVar60 ^ uVar16) & uVar45 ^ uVar16) & uVar43 ^ uVar45 & uVar36) & 0xFFFFFFFF
    uVar49 = (
        (~(((~(uVar1 & uVar8) ^ uVar60) & uVar70 ^ uVar60) & uVar45) ^ uVar70) & uVar43
        ^ (~((~(uVar32 & uVar70) ^ uVar45) & uVar43) ^ uVar32 & uVar70 ^ uVar45) & uVar1 & uVar16
        ^ uVar45 & uVar70
    ) & 0xFFFFFFFF
    uVar32 = (
        (
            (((uVar60 ^ uVar45) & uVar18 ^ uVar32 & uVar60 ^ uVar45) & uVar84 ^ uVar60 & uVar45 & uVar18) & uVar42
            ^ ~(uVar60 & uVar45 & uVar84) & uVar18
            ^ uVar45
        )
        & uVar16
        ^ ~(~((~uVar84 & uVar42 ^ uVar84) & uVar60) & uVar18) & uVar45
    ) & 0xFFFFFFFF
    uVar8 = (
        (~((uVar31 ^ uVar21) & uVar39) ^ (uVar31 ^ uVar7) & uVar21 ^ uVar7) & uVar30
        ^ (~(uVar69 & uVar30) ^ ~uVar21 & uVar7 ^ uVar21) & uVar13
        ^ (uVar31 & uVar39 ^ uVar7) & ~uVar21
        ^ uVar31
    ) & 0xFFFFFFFF
    uVar5 = ((uVar59 ^ uVar26) & uVar78) & 0xFFFFFFFF
    uVar5 = ((~uVar5 ^ uVar44 ^ uVar59) & uVar35 ^ (uVar5 ^ uVar44 ^ uVar59) & uVar66 ^ uVar78) & 0xFFFFFFFF
    uVar18 = ((uVar28 ^ uVar55) & (uVar45 ^ uVar16) & uVar60 ^ uVar16 ^ uVar18) & 0xFFFFFFFF
    uVar85 = (
        ~(((~uVar78 ^ uVar35) & uVar44 ^ uVar78 ^ uVar35) & uVar66)
        ^ ((~uVar44 ^ uVar59 ^ uVar26) & uVar35 ^ uVar59) & uVar78
        ^ ~uVar35 & uVar59
        ^ uVar35
    ) & 0xFFFFFFFF
    uVar84 = (
        ~((uVar15 ^ uVar62) & uVar57) & uVar77 ^ (uVar9 & uVar15 ^ uVar57 ^ uVar33) & uVar62 ^ uVar15 & uVar14 ^ uVar57
    ) & 0xFFFFFFFF
    uVar1 = (
        ~((~((uVar1 & uVar51 ^ uVar48 & uVar76) & uVar70) ^ uVar1 ^ uVar48) & uVar43) ^ (uVar74 ^ uVar64) & uVar48 ^ uVar1
    ) & 0xFFFFFFFF
    uVar43 = ((~uVar14 ^ uVar33) & uVar62) & 0xFFFFFFFF
    uVar36 = (~uVar22) & 0xFFFFFFFF
    uVar74 = (
        ~((uVar57 & ~uVar15 ^ uVar43 ^ uVar15 ^ uVar14) & uVar77) ^ (~uVar43 ^ uVar14) & uVar57 ^ uVar15 ^ uVar62
    ) & 0xFFFFFFFF
    uVar43 = (uVar6 ^ uVar87 ^ uVar32 ^ uVar36) & 0xFFFFFFFF
    uVar55 = (
        ~(((uVar87 ^ uVar32 ^ uVar36) & uVar6 ^ (uVar32 ^ uVar36) & uVar87 ^ ~(uVar18 & uVar43) ^ uVar32) & uVar88)
        ^ (uVar22 ^ uVar18 ^ uVar32) & uVar6 & uVar87
        ^ (uVar18 ^ uVar32) & uVar22
        ^ uVar32
    ) & 0xFFFFFFFF
    uVar36 = (uVar6 & uVar87) & 0xFFFFFFFF
    uVar64 = ((uVar88 & uVar43 ^ uVar32 ^ uVar36) & uVar18 ^ (uVar32 ^ uVar36) & uVar88 ^ uVar22 ^ uVar36) & 0xFFFFFFFF
    uVar51 = (
        ~(((uVar65 ^ uVar84) & (uVar17 ^ uVar41) ^ uVar65 ^ uVar84) & uVar74)
        ^ (~uVar17 ^ uVar41) & uVar65 & uVar84
        ^ ~uVar41 & uVar17
        ^ uVar53
    ) & 0xFFFFFFFF
    uVar43 = ((~uVar6 ^ uVar87) & uVar88) & 0xFFFFFFFF
    uVar18 = (
        ~((~uVar43 ^ uVar18 ^ uVar32 ^ uVar36) & uVar22) ^ (uVar18 ^ uVar43 ^ uVar36) & uVar32 ^ uVar88 ^ uVar18
    ) & 0xFFFFFFFF
    uVar15 = (uVar65 & uVar84) & 0xFFFFFFFF
    uVar74 = (uVar74 & (uVar65 ^ uVar84)) & 0xFFFFFFFF
    uVar57 = ((~uVar53 & uVar41 ^ uVar15 ^ uVar74) & uVar17 ^ (~uVar74 ^ uVar15) & uVar53 ^ uVar41) & 0xFFFFFFFF
    uVar84 = (
        ((uVar66 ^ uVar35) & uVar44 ^ (uVar59 ^ uVar26) & uVar66 ^ uVar26) & uVar78
        ^ (~(~uVar35 & uVar44) ^ uVar59) & uVar66
        ^ uVar35
    ) & 0xFFFFFFFF
    uVar2 = ((uVar47 ^ uVar52) & uVar2) & 0xFFFFFFFF
    uVar43 = (uVar72 ^ uVar2) & 0xFFFFFFFF
    uVar36 = (uVar45 & uVar43) & 0xFFFFFFFF
    uVar9 = (~uVar36 & uVar60 ^ (uVar60 ^ uVar45) & uVar16) & 0xFFFFFFFF
    uVar22 = (uVar50 ^ uVar34) & 0xFFFFFFFF
    uVar32 = (uVar27 & uVar22) & 0xFFFFFFFF
    uVar59 = (
        ((uVar50 ^ uVar27 ^ uVar34) & uVar3 ^ uVar50 ^ uVar27 ^ uVar34) & uVar4
        ^ (uVar50 ^ uVar34 ^ uVar32) & uVar75
        ^ (uVar27 ^ uVar75) & uVar3 & uVar22
        ^ uVar50
        ^ uVar27
    ) & 0xFFFFFFFF
    uVar53 = ((uVar15 ^ uVar74) & (uVar17 ^ uVar41) ^ uVar17 ^ uVar53) & 0xFFFFFFFF
    uVar15 = (~(uVar60 & uVar43) & uVar45 ^ (uVar60 ^ uVar36) & uVar16) & 0xFFFFFFFF
    uVar41 = (((uVar53 ^ uVar57) & uVar51) * 2 & 0xFFFFFFFF) & 0xFFFFFFFF
    uVar52 = (~((~uVar2 ^ uVar72) & uVar60) & uVar16 ^ uVar45) & 0xFFFFFFFF
    uVar26 = (~((uVar53 & uVar51) * 2 & 0xFFFFFFFF & ~(uVar57 * 2 & 0xFFFFFFFF))) & 0xFFFFFFFF
    uVar28 = ((uVar51 * 2 & 0xFFFFFFFF) ^ ~(uVar57 * 2 & 0xFFFFFFFF)) & 0xFFFFFFFF
    uVar51 = (_shr(uVar51, 0x1F)) & 0xFFFFFFFF
    uVar72 = (~(_shr(uVar53, 0x1F)) & uVar51 & _shr(uVar57, 0x1F)) & 0xFFFFFFFF
    uVar74 = (uVar55 & (~uVar52 ^ uVar64)) & 0xFFFFFFFF
    uVar78 = (
        ~((~((uVar55 ^ ~uVar52 ^ uVar64) & uVar18) ^ (~uVar15 ^ uVar64) & uVar52 ^ uVar15 ^ uVar74) & uVar9)
        ^ ((uVar18 ^ uVar64 ^ uVar55) & uVar52 ^ uVar18 ^ uVar64 ^ uVar55) & uVar15
        ^ (~uVar55 & uVar18 ^ uVar55) & uVar64
        ^ uVar18
    ) & 0xFFFFFFFF
    uVar30 = (
        ~(((~uVar39 ^ uVar7) & uVar31 ^ (uVar58 ^ uVar39) & uVar30 ^ (uVar31 ^ uVar7) & uVar13) & uVar21)
        ^ (~uVar30 & uVar39 ^ uVar13 & ~uVar7 ^ uVar7) & uVar31
        ^ uVar30
    ) & 0xFFFFFFFF
    uVar43 = ((uVar30 ^ ~uVar89) & uVar8) & 0xFFFFFFFF
    uVar2 = (
        (~((uVar30 ^ ~uVar40) & uVar11) ^ uVar40 ^ uVar43) & uVar1 ^ (uVar89 & uVar8 ^ ~uVar11 & uVar40) & uVar30 ^ uVar8
    ) & 0xFFFFFFFF
    uVar17 = (
        ((uVar8 ^ ~uVar40) & uVar11 ^ uVar40 ^ uVar43) & uVar1 ^ (uVar89 ^ uVar30 ^ ~uVar11 & uVar40) & uVar8 ^ uVar30
    ) & 0xFFFFFFFF
    uVar43 = (~((uVar84 ^ uVar5) & uVar49)) & 0xFFFFFFFF
    uVar39 = (
        ((uVar84 ^ uVar5) & uVar61 ^ uVar43 ^ uVar84 ^ uVar5) & uVar67 ^ (uVar43 ^ uVar84 ^ uVar5) & uVar61 ^ ~uVar84 & uVar5
    ) & 0xFFFFFFFF
    uVar58 = (~uVar84 ^ uVar85) & 0xFFFFFFFF
    uVar43 = (uVar58 ^ uVar49) & 0xFFFFFFFF
    uVar31 = (
        ((uVar85 ^ uVar49 ^ uVar61) & uVar84 ^ (uVar43 ^ uVar61) & uVar5 ^ uVar85 ^ uVar49) & uVar67
        ^ ((uVar85 ^ uVar49) & uVar84 ^ uVar43 & uVar5 ^ uVar85 ^ uVar49) & uVar61
        ^ ~uVar5 & uVar84
    ) & 0xFFFFFFFF
    uVar36 = (~uVar50) & 0xFFFFFFFF
    uVar61 = (
        (~((~uVar67 ^ uVar61) & uVar84) ^ uVar67 ^ uVar61) & uVar85
        ^ ((uVar67 ^ uVar61) & uVar58 ^ uVar84 ^ uVar85) & uVar5
        ^ ~uVar61 & uVar67
        ^ uVar84
        ^ uVar61
    ) & 0xFFFFFFFF
    uVar3 = (
        (~((uVar27 ^ uVar36 ^ uVar34) & uVar3) ^ uVar50 ^ uVar27 ^ uVar34) & uVar4
        ^ (uVar75 & uVar22 ^ ~uVar32 ^ uVar50) & uVar3
        ^ (uVar27 ^ uVar36) & uVar34
        ^ uVar75 & uVar32
    ) & 0xFFFFFFFF
    uVar84 = (~(_shr(uVar39, 0x1F)) & _shr(uVar61, 0x1F) ^ _shr(uVar31, 0x1F)) & 0xFFFFFFFF
    uVar85 = (uVar61 & uVar39 ^ uVar31) & 0xFFFFFFFF
    uVar5 = (uVar85 * 2 & 0xFFFFFFFF) & 0xFFFFFFFF
    uVar85 = (_shr(uVar85, 0x1F)) & 0xFFFFFFFF
    uVar27 = (uVar61 * 2 & 0xFFFFFFFF) & 0xFFFFFFFF
    uVar43 = (~uVar27 & (uVar39 * 2 & 0xFFFFFFFF) ^ ~(uVar31 * 2 & 0xFFFFFFFF) & uVar27) & 0xFFFFFFFF
    uVar32 = (~(uVar39 * 2 & 0xFFFFFFFF) & uVar27 ^ (uVar31 * 2 & 0xFFFFFFFF)) & 0xFFFFFFFF
    uVar27 = (~((uVar79 ^ uVar59) & uVar3)) & 0xFFFFFFFF
    uVar58 = (
        ~((uVar12 & uVar73 ^ uVar79 ^ uVar27 ^ uVar59) & uVar23) ^ (uVar12 ^ uVar79 ^ uVar27 ^ uVar59) & uVar73 ^ uVar3 ^ uVar59
    ) & 0xFFFFFFFF
    uVar11 = ((~uVar30 ^ uVar8) & uVar11) & 0xFFFFFFFF
    uVar22 = (
        ~((~uVar11 ^ uVar30 ^ uVar8) & uVar40) ^ ~(uVar30 & ~uVar89) & uVar8 ^ (uVar11 ^ uVar30 ^ uVar8) & uVar1
    ) & 0xFFFFFFFF
    uVar27 = ((~uVar12 ^ uVar73) & uVar23) & 0xFFFFFFFF
    uVar40 = (~uVar27) & 0xFFFFFFFF
    uVar61 = (~(_shr(uVar31, 0x1F)) & _shr(uVar61, 0x1F) ^ _shr((uVar31 ^ uVar39), 0x1F)) & 0xFFFFFFFF
    uVar11 = (
        (~uVar3 & uVar79 ^ uVar12 ^ uVar73 ^ uVar40) & uVar59
        ^ (uVar12 ^ uVar79 ^ uVar73 ^ uVar40) & uVar3
        ^ (uVar12 ^ uVar73) & uVar23
        ^ uVar12
        ^ uVar79
    ) & 0xFFFFFFFF
    uVar40 = (~(_shr(uVar57, 0x1F))) & 0xFFFFFFFF
    uVar57 = (uVar40 ^ uVar51) & 0xFFFFFFFF
    uVar39 = (~(uVar40 & uVar51 & _shr(uVar53, 0x1F))) & 0xFFFFFFFF
    uVar8 = (
        (~((uVar12 ^ uVar79 ^ uVar73) & uVar23) ^ uVar79 & uVar73 ^ uVar12) & uVar3
        ^ ((uVar79 ^ uVar73 ^ ~uVar23) & uVar3 ^ uVar12 ^ uVar79 ^ uVar73 ^ uVar27) & uVar59
        ^ (uVar23 ^ uVar73) & uVar79
        ^ uVar12 & uVar73 & ~uVar23
    ) & 0xFFFFFFFF
    uVar73 = (uVar11 ^ uVar58) & 0xFFFFFFFF
    uVar23 = (_shr(uVar73, 0x1F)) & 0xFFFFFFFF
    uVar3 = (
        (~((~uVar9 ^ uVar55) & uVar52) ^ uVar9 ^ uVar55) & uVar15
        ^ ((~uVar64 ^ uVar55) & uVar18 ^ uVar74) & uVar9
        ^ (~uVar64 & uVar55 ^ uVar64) & uVar18
        ^ uVar64
    ) & 0xFFFFFFFF
    uVar53 = (_shr(uVar11, 0x1F) & ~(_shr(uVar58, 0x1F)) ^ _shr(uVar58, 0x1F) ^ 0xFFFFFFFE) & 0xFFFFFFFF
    uVar40 = ((uVar17 & uVar2 ^ uVar22) * 2 & 0xFFFFFFFF) & 0xFFFFFFFF
    uVar1 = (_shr((uVar8 & uVar73), 0x1F)) & 0xFFFFFFFF
    uVar51 = (~(_shr((uVar17 & uVar22), 0x1F)) ^ _shr(uVar2, 0x1F)) & 0xFFFFFFFF
    uVar4 = ((_shr(uVar17, 0x1F) & ~(_shr(uVar22, 0x1F)) ^ ~(_shr(uVar2, 0x1F))) & 1) & 0xFFFFFFFF
    uVar52 = ((uVar15 ^ uVar9) & uVar52) & 0xFFFFFFFF
    uVar55 = (
        (~uVar52 ^ uVar15 ^ uVar9 ^ uVar55) & uVar64 ^ (uVar52 ^ uVar15 ^ uVar9 ^ uVar64 ^ uVar55) & uVar18 ^ uVar9 ^ uVar55
    ) & 0xFFFFFFFF
    uVar27 = ((uVar8 & uVar11 ^ uVar58) * 2 & 0xFFFFFFFF) & 0xFFFFFFFF
    uVar73 = ((uVar8 & uVar73 ^ uVar11) * 2 & 0xFFFFFFFF ^ 1) & 0xFFFFFFFF
    uVar64 = (_shr((uVar55 ^ uVar3), 0x1F)) & 0xFFFFFFFF
    uVar9 = ((_shr(((uVar22 ^ uVar2) & uVar17), 0x1F) ^ ~(_shr(uVar22, 0x1F))) & 1) & 0xFFFFFFFF
    uVar52 = (_shr((uVar78 & (uVar55 ^ uVar3)), 0x1F)) & 0xFFFFFFFF
    uVar11 = (~(uVar11 * 2 & 0xFFFFFFFF) & (uVar8 * 2 & 0xFFFFFFFF) ^ (uVar58 * 2 & 0xFFFFFFFF) ^ 1) & 0xFFFFFFFF
    uVar58 = (~(_shr(uVar55, 0x1F)) & ~(_shr(uVar3, 0x1F)) & 1) & 0xFFFFFFFF
    uVar12 = ((uVar17 & (uVar22 ^ uVar2) ^ uVar2) * 2 & 0xFFFFFFFF ^ 1) & 0xFFFFFFFF
    uVar8 = (~(uVar2 * 2 & 0xFFFFFFFF) & (uVar17 * 2 & 0xFFFFFFFF) ^ (uVar22 * 2 & 0xFFFFFFFF) ^ 1) & 0xFFFFFFFF
    uVar74 = (uVar45 & 0xF66FFCFF) & 0xFFFFFFFF
    uVar22 = (~uVar87 & uVar6 ^ uVar87) & 0xFFFFFFFF
    uVar2 = ((uVar74 ^ 0x1697DDD0) & uVar87) & 0xFFFFFFFF
    dst_dwords[0] = (
        (
            ((uVar45 & 0x9FDA9BE4 ^ ~(uVar60 & 0x9FDA9BE4)) & 0xFBF5F7DB ^ uVar6 & 0x6DBF6F3F) & uVar16
            ^ (uVar45 & ~(uVar60 & 0x9FDA9BE4) ^ uVar87 & 0x9FDA9BE4) & 0xFBF5F7DB
            ^ (uVar87 & 0x9BD093C0 ^ uVar74 ^ 0x1697DDD0) & uVar6
            ^ 0x7DEA396F
        )
        & uVar88
        ^ ((uVar45 & 0x9BD093C0 ^ 0x7B28B2EF) & uVar60 ^ uVar22 & 0x6DBF6F3F ^ uVar45 & 0x76B2B9CB ^ 0xC95F4C2C) & uVar16
        ^ (uVar60 & 0xE0F8212F ^ 0x4F408298) & uVar45
        ^ (uVar2 ^ uVar74 ^ 0x1697DDD0) & uVar6
        ^ uVar2
        ^ 0xD10776C9
    ) & 0xFFFFFFFF
    uVar2 = (uVar45 & 0x3BDDDFDF) & 0xFFFFFFFF
    uVar74 = ((uVar2 ^ 0xEE3E32AC) & uVar87) & 0xFFFFFFFF
    dst_dwords[1] = (
        (
            ((uVar45 & 0xED37677F ^ ~(uVar60 & 0xED37677F)) & 0xDEEEFAAF ^ uVar6 & 0xF7FBBDF0) & uVar16
            ^ (uVar45 & ~(uVar60 & 0xED37677F) ^ uVar87 & 0xED37677F) & 0xDEEEFAAF
            ^ (uVar87 & 0xCC26622F ^ uVar2 ^ 0xEE3E32AC) & uVar6
            ^ 0xF1D3CF5F
        )
        & uVar88
        ^ ((uVar45 & 0xCC26622F ^ 0x19C58F5C) & uVar60 ^ uVar45 & 0xFCF6AA2C ^ uVar22 & 0xF7FBBDF0 ^ 0x16A964E3) & uVar16
        ^ (uVar74 ^ uVar2 ^ 0xEE3E32AC) & uVar6
        ^ (uVar60 & 0xD5E3ED73 ^ 0x39945113) & uVar45
        ^ uVar74
        ^ 0x1F5D9F8A
    ) & 0xFFFFFFFF
    uVar22 = (uVar45 & 0xEFBBB36D) & 0xFFFFFFFF
    uVar74 = ((uVar22 ^ 0x164A1EF) & uVar87) & 0xFFFFFFFF
    dst_dwords[2] = (
        (
            ((uVar45 & 0x70CD4C92 ^ ~(uVar60 & 0x70CD4C92)) & 0xFDDF4FF6 ^ uVar6 & 0x9F76FFFF) & uVar16
            ^ (uVar45 & ~(uVar60 & 0x70CD4C92) ^ uVar87 & 0x70CD4C92) & 0xFDDF4FF6
            ^ (uVar22 ^ uVar87 & 0x70CD4C92 ^ 0x164A1EF) & uVar6
            ^ 0xAE3FBA99
        )
        & uVar88
        ^ (
            (uVar45 & 0xECFFA28B ^ ~uVar87 & uVar6 ^ uVar87) & 0x9F76FFFF
            ^ (uVar45 & 0x70CD4C92 ^ 0x9E125E10) & uVar60
            ^ 0xE0CB9B12
        )
        & uVar16
        ^ (uVar60 & 0xEEDF1282 ^ 0xB32B6E7D) & uVar45
        ^ (uVar74 ^ uVar22 ^ 0x164A1EF) & uVar6
        ^ uVar74
        ^ 0xEA6003B
    ) & 0xFFFFFFFF
    uVar22 = (~uVar33 & uVar14) & 0xFFFFFFFF
    uVar74 = (uVar22 ^ uVar48) & 0xFFFFFFFF
    dst_dwords[3] = (
        (
            ((uVar48 ^ 0x3084440F) & 0x7BDDE4FF ^ uVar46 & 0x8C739BB0) & uVar29
            ^ ((uVar46 ^ 0x3084440F) & 0xF7AE7F4F ^ uVar48 & 0x7BDDE4FF) & uVar10
            ^ (uVar33 & 0x7BDDE4FF ^ 0x8F191B20) & uVar14
            ^ uVar33 & 0xF4C4FFDF
            ^ uVar48 & 0x7BDDE4FF
            ^ 0x8E7A9B06
        )
        & uVar62
        ^ ((uVar48 ^ 0x3084440F) & uVar10 & 0x7BDDE4FF ^ uVar22 & 0x8C739BB0 ^ uVar48 & 0x8F191B20 ^ 0x77AF7EFF) & uVar29
        ^ (uVar22 & 0xF7AE7F4F ^ uVar48 & 0x8F191B20 ^ 0xC951A1F6) & uVar10
        ^ uVar74 & 0x8F191B20
        ^ 0xC7F9EC49
    ) & 0xFFFFFFFF
    uVar87 = ((uVar48 ^ 0x4632940) & 0xBEEFFFF8) & 0xFFFFFFFF
    dst_dwords[4] = (
        (
            (uVar46 & 0xE39C1007 ^ uVar87) & uVar29
            ^ (uVar46 & 0x5D73EFFF ^ uVar87) & uVar10
            ^ (uVar33 & 0xBEEFFFF8 ^ 0x5EB066DE) & uVar14
            ^ uVar33 & 0xE05F9926
            ^ uVar48 & 0xBEEFFFF8
            ^ 0x613631F7
        )
        & uVar62
        ^ ((uVar48 ^ 0x4632940) & uVar10 & 0xBEEFFFF8 ^ uVar22 & 0xE39C1007 ^ uVar48 & 0x5EB066DE ^ 0xDBDBCFB8) & uVar29
        ^ (uVar22 & 0x5D73EFFF ^ uVar48 & 0x5EB066DE ^ 0xBE8ED70F) & uVar10
        ^ uVar74 & 0x5EB066DE
        ^ 0xE1B4DB1D
    ) & 0xFFFFFFFF
    uVar87 = ((uVar48 ^ 0xCB9D92F8) & 0xFF7AFFB7) & 0xFFFFFFFF
    dst_dwords[5] = (
        (
            (uVar46 & 0x10A76D4F ^ uVar87) & uVar29
            ^ (uVar46 & 0xEFDD92F8 ^ uVar87) & uVar10
            ^ (uVar33 & 0xFF7AFFB7 ^ 0x60568029) & uVar14
            ^ uVar33 & 0x9F2C7F9E
            ^ uVar48 & 0xFF7AFFB7
            ^ 0x99AFECF8
        )
        & uVar62
        ^ ((uVar48 ^ 0xCB9D92F8) & uVar10 & 0xFF7AFFB7 ^ uVar22 & 0x10A76D4F ^ uVar48 & 0x60568029 ^ 0xAF4C13DF) & uVar29
        ^ (uVar22 & 0xEFDD92F8 ^ uVar48 & 0x60568029 ^ 0xFDFB6D97) & uVar10
        ^ uVar74 & 0x60568029
        ^ 0xE203457D
    ) & 0xFFFFFFFF
    uVar87 = (uVar7 ^ uVar21) & 0xFFFFFFFF
    uVar74 = (uVar48 & 0x4F56D2EF) & 0xFFFFFFFF
    uVar22 = (uVar56 ^ uVar21) & 0xFFFFFFFF
    uVar56 = (uVar56 ^ uVar48) & 0xFFFFFFFF
    uVar2 = ((uVar74 ^ 0xE2646C22) & uVar21) & 0xFFFFFFFF
    dst_dwords[6] = (
        (
            (uVar87 & 0xF4EB3FFD ^ uVar74 ^ 0xBFFFFD3B) & uVar29
            ^ (uVar21 & 0xF4EB3FFD ^ uVar74 ^ 0xE6267C0B) & uVar7
            ^ uVar56 & 0x4F56D2EF
            ^ uVar2
            ^ 0x5E8953F1
        )
        & uVar13
        ^ ((uVar7 & 0xF4EB3FFD ^ 0x12CD43F6) & uVar48 ^ uVar22 & 0xF4EB3FFD ^ 0xBDD1B905) & uVar29
        ^ (uVar48 & 0x4B14C2C6 ^ uVar21 & 0xF4EB3FFD ^ 0xBDD1B905) & uVar7
        ^ (uVar7 & 0xF4EB3FFD ^ 0xE2646C22) & uVar54 & uVar10
        ^ uVar48 & 0xF3BBED3C
        ^ uVar2
        ^ 0xB38646A4
    ) & 0xFFFFFFFF
    uVar74 = (uVar48 & 0xF9EF7D3F) & 0xFFFFFFFF
    uVar2 = ((uVar74 ^ 0xB53A104D) & uVar21) & 0xFFFFFFFF
    dst_dwords[7] = (
        (
            (uVar87 & 0xFFFDEEFE ^ uVar74 ^ 0x77BF9BD7) & uVar29
            ^ (uVar21 & 0xFFFDEEFE ^ uVar74 ^ 0xC497185B) & uVar7
            ^ uVar56 & 0xF9EF7D3F
            ^ uVar2
            ^ 0xB306C692
        )
        & uVar13
        ^ ((uVar7 & 0xFFFDEEFE ^ 0x3B6AF6A5) & uVar48 ^ uVar22 & 0xFFFDEEFE ^ 0xA6CA3BE) & uVar29
        ^ (uVar48 & 0x88427529 ^ uVar21 & 0xFFFDEEFE ^ 0xA6CA3BE) & uVar7
        ^ (uVar7 & 0xFFFDEEFE ^ 0xB53A104D) & uVar54 & uVar10
        ^ uVar48 & 0xFFD3ABE0
        ^ uVar2
        ^ 0x65E54891
    ) & 0xFFFFFFFF
    uVar74 = (uVar48 & 0xFEBFFFD2) & 0xFFFFFFFF
    uVar2 = ((uVar74 ^ 0x2C87FFF2) & uVar21) & 0xFFFFFFFF
    dst_dwords[8] = (
        (
            (uVar87 & 0x8FF7FFEF ^ uVar74 ^ 0xFB58E7FD) & uVar29
            ^ (uVar21 & 0x8FF7FFEF ^ uVar74 ^ 0xA6971832) & uVar7
            ^ uVar56 & 0xFEBFFFD2
            ^ uVar2
            ^ 0x417CBB8F
        )
        & uVar13
        ^ ((uVar7 & 0x8FF7FFEF ^ 0x2960E7DD) & uVar48 ^ uVar22 & 0x8FF7FFEF ^ 0x5D9B4468) & uVar29
        ^ (uVar48 & 0x74AF1812 ^ uVar21 & 0x8FF7FFEF ^ 0x5D9B4468) & uVar7
        ^ (uVar7 & 0x8FF7FFEF ^ 0x2C87FFF2) & uVar54 & uVar10
        ^ uVar48 & 0x9344BBAF
        ^ uVar2
        ^ 0x766454F9
    ) & 0xFFFFFFFF
    uVar87 = (uVar48 & 0xFCF7BFF) & 0xFFFFFFFF
    uVar74 = ((uVar54 ^ uVar34) & uVar50) & 0xFFFFFFFF
    dst_dwords[9] = (
        (
            (uVar48 & 0xF7BED53A ^ uVar34 & 0xFCF7BFF ^ 0xFD77FFCF) & uVar50
            ^ (uVar48 & 0xF871AEC5 ^ 0xF2B88430) & uVar10
            ^ uVar48 & 0xDFB055FA
            ^ 0x21C9F35E
        )
        & uVar29
        ^ ((uVar10 & 0xF7BED53A ^ uVar29 & 0xFCF7BFF) & uVar36 ^ (uVar87 ^ 0xD07F2E05) & uVar50 ^ uVar87 ^ 0xD07F2E05) & uVar75
        ^ ((uVar87 ^ 0x27C1FB3F) & uVar34 ^ uVar48 & 0xAC92AF5 ^ 0xBB1655EA) & uVar50
        ^ (uVar48 & 0x2D08D1CA ^ uVar74 & 0xF7BED53A ^ 0x9CD7AED5) & uVar10
        ^ uVar48 & 0xFE79A6A4
        ^ 0x4794400E
    ) & 0xFFFFFFFF
    uVar87 = (uVar48 & 0xF6F8AF3D) & 0xFFFFFFFF
    dst_dwords[10] = (
        (
            (uVar34 & 0xF6F8AF3D ^ uVar48 & 0x9BFFFFF7 ^ 0xEF9FD0FB) & uVar50
            ^ (uVar48 & 0x6D0750CA ^ 0x19677FC6) & uVar10
            ^ uVar48 & 0x446ACC8B
            ^ 0xBFF59151
        )
        & uVar29
        ^ ((uVar10 & 0x9BFFFFF7 ^ uVar29 & 0xF6F8AF3D) & uVar36 ^ (uVar87 ^ 0xB29263B6) & uVar50 ^ uVar87 ^ 0xB29263B6) & uVar75
        ^ ((uVar87 ^ 0x296D9C41) & uVar34 ^ uVar48 & 0x74602F0C ^ 0x4C01AE2D) & uVar50
        ^ (uVar74 & 0x9BFFFFF7 ^ uVar48 & 0x5D0DB34D ^ 0x656C326C) & uVar10
        ^ uVar48 & 0xFB9F5DDA
        ^ 0xBE725D50
    ) & 0xFFFFFFFF
    uVar87 = (uVar48 & 0xFDFFFFE6) & 0xFFFFFFFF
    uVar54 = (uVar60 & 0xBBFEADF4) & 0xFFFFFFFF
    uVar21 = ((uVar45 ^ 0x99FA0CF4) & 0xFEEDF73F) & 0xFFFFFFFF
    dst_dwords[0xB] = (
        (
            (uVar48 & 0x7F737EDD ^ uVar34 & 0xFDFFFFE6 ^ 0xFAEDAFFF) & uVar50
            ^ (uVar48 & 0x828C813B ^ 0x7125019) & uVar10
            ^ uVar48 & 0x729F22AE
            ^ 0x4D0E1CB1
        )
        & uVar29
        ^ ((uVar29 & 0xFDFFFFE6 ^ uVar10 & 0x7F737EDD) & uVar36 ^ (uVar87 ^ 0x8F60DD48) & uVar50 ^ uVar87 ^ 0x8F60DD48) & uVar75
        ^ ((uVar87 ^ 0xF013A395) & uVar34 ^ uVar48 & 0x859ED122 ^ 0x42FC40F2) & uVar50
        ^ (uVar74 & 0x7F737EDD ^ uVar48 & 0x758D72B7 ^ 0xB2EFE367) & uVar10
        ^ uVar48 & 0x3F913E1F
        ^ 0xA7188BB0
    ) & 0xFFFFFFFF
    uVar87 = (((uVar45 ^ 0x6605F30B) & uVar60 ^ uVar45) & 0xFEEDF73F) & 0xFFFFFFFF
    uVar50 = (uVar45 & 0x59FE051B) & 0xFFFFFFFF
    dst_dwords[0xC] = (
        ((uVar35 & 0xBBFEADF4 ^ uVar21) & uVar16 ^ (uVar66 & 0xFEEDF73F ^ uVar54 ^ 0x59FE051B) & uVar35 ^ uVar87 ^ 0x21FE6DD8)
        & uVar44
        ^ ((uVar66 & 0xBBFEADF4 ^ uVar21) & uVar35 ^ uVar54 ^ uVar50 ^ 0x5F01DA0B) & uVar16
        ^ ((uVar54 ^ 0xA713F224) & uVar66 ^ uVar87 ^ 0x21FE6DD8) & uVar35
        ^ (uVar50 ^ 0xBD0172E4) & uVar60
        ^ uVar50
        ^ 0x1E65E625
    ) & 0xFFFFFFFF
    uVar36 = (uVar60 & 0x67B7D3FF) & 0xFFFFFFFF
    uVar50 = ((uVar45 ^ 0x6706D3C0) & 0xFFDFFFE0) & 0xFFFFFFFF
    uVar21 = (((uVar45 ^ 0x98F92C3F) & uVar60 ^ uVar45) & 0xFFDFFFE0) & 0xFFFFFFFF
    uVar74 = (uVar45 & 0xFB40C824) & 0xFFFFFFFF
    uVar87 = (uVar45 & 0x3E91B3C4) & 0xFFFFFFFF
    dst_dwords[0xD] = (
        ((uVar35 & 0x67B7D3FF ^ uVar50) & uVar16 ^ (uVar66 & 0xFFDFFFE0 ^ uVar36 ^ 0xFB40C824) & uVar35 ^ uVar21 ^ 0x7DA957FF)
        & uVar44
        ^ ((uVar66 & 0x67B7D3FF ^ uVar50) & uVar35 ^ uVar74 ^ uVar36 ^ 0x9E58BFC3) & uVar16
        ^ ((uVar36 ^ 0x49F37C4) & uVar66 ^ uVar21 ^ 0x7DA957FF) & uVar35
        ^ (uVar74 ^ 0x2AFA418) & uVar60
        ^ uVar74
        ^ 0x6A57C73D
    ) & 0xFFFFFFFF
    uVar21 = (uVar60 & 0xFDFDFF6F) & 0xFFFFFFFF
    uVar50 = (((uVar45 ^ 0xFFEED7F4) & uVar60 ^ uVar45) & 0x43736EDF) & 0xFFFFFFFF
    dst_dwords[0xE] = (
        (
            ((uVar35 ^ 0x11280B) & 0xFDFDFF6F ^ uVar45 & 0x43736EDF) & uVar16
            ^ (uVar66 & 0x43736EDF ^ uVar21 ^ 0x3E91B3C4) & uVar35
            ^ uVar50
            ^ 0xFFCE93B8
        )
        & uVar44
        ^ (((uVar66 ^ 0x11280B) & 0xFDFDFF6F ^ uVar45 & 0x43736EDF) & uVar35 ^ uVar87 ^ uVar21 ^ 0xA6B775FC) & uVar16
        ^ ((uVar21 ^ 0x7DE2DD1B) & uVar66 ^ uVar50 ^ 0xFFCE93B8) & uVar35
        ^ (uVar87 ^ 0x65DB3957) & uVar60
        ^ uVar87
        ^ 0x6FA144D4
    ) & 0xFFFFFFFF
    uVar45 = (uVar63 ^ uVar20) & 0xFFFFFFFF
    uVar66 = (uVar90 ^ uVar63) & 0xFFFFFFFF
    uVar87 = (uVar20 & 0xFF7FDB7F) & 0xFFFFFFFF
    dst_dwords[0xF] = (
        (
            ((uVar38 ^ 0x4C054955) & 0xFF7FDB7F ^ uVar20 & 0x5D9D7FDD) & uVar63
            ^ (uVar45 & 0x5D9D7FDD ^ 0x9A8731B3) & uVar90
            ^ uVar20 & 0x8B1F073B
            ^ uVar19 & 0xFF7FDB7F
            ^ 0x3E07CD0
        )
        & uVar92
        ^ (
            (uVar66 & 0x5D9D7FDD ^ uVar87 ^ 0x7460DC44) & uVar38
            ^ (uVar87 ^ 0x7460DC44) & uVar63
            ^ uVar25 & 0x5D9D7FDD
            ^ uVar87
            ^ 0x7460DC44
        )
        & uVar68
        ^ ((uVar90 & 0x5D9D7FDD ^ uVar87 ^ 0x29FDA399) & uVar38 ^ (uVar90 ^ 0x11983688) & uVar20 & 0x5D9D7FDD ^ 0xF67A86BE)
        & uVar63
        ^ (uVar20 & 0xC71A4E6E ^ 0xF67A86BE) & uVar90
        ^ uVar20 & 0x88FF7BEB
        ^ 0x4D89219C
    ) & 0xFFFFFFFF
    uVar87 = (uVar20 & 0xDAF2BEAF) & 0xFFFFFFFF
    dst_dwords[0x10] = (
        (
            ((uVar38 ^ 0x2F2A42A) & 0xDAF2BEAF ^ uVar20 & 0xA7FFE5FF) & uVar63
            ^ (uVar45 & 0xA7FFE5FF ^ 0xE30EFB13) & uVar90
            ^ uVar20 & 0x4603BAC6
            ^ uVar19 & 0xDAF2BEAF
            ^ 0xB59F6FDB
        )
        & uVar92
        ^ (
            (uVar66 & 0xA7FFE5FF ^ uVar87 ^ 0x9CF10469) & uVar38
            ^ (uVar87 ^ 0x9CF10469) & uVar63
            ^ uVar25 & 0xA7FFE5FF
            ^ uVar87
            ^ 0x9CF10469
        )
        & uVar68
        ^ ((uVar90 & 0xA7FFE5FF ^ uVar87 ^ 0x3B0EE196) & uVar38 ^ (uVar90 ^ 0xFD0D5BD5) & uVar20 & 0xA7FFE5FF ^ 0x79663B66)
        & uVar63
        ^ (uVar20 & 0x44F11EEC ^ 0x79663B66) & uVar90
        ^ uVar20 & 0xF39CD51D
        ^ 0x435C6204
    ) & 0xFFFFFFFF
    uVar87 = (uVar20 & 0xF7EFF7D8) & 0xFFFFFFFF
    dst_dwords[0x11] = (
        (
            ((uVar20 ^ 0xB10812C8) & 0xFFFFFFB7 ^ uVar71 & 0x77EFF7D8) & uVar63
            ^ (uVar45 & 0xFFFFFFB7 ^ 0xBA17B939) & uVar90
            ^ uVar20 & 0xF4E0540E
            ^ uVar19 & 0xF7EFF7D8
            ^ 0xD81E9F2F
        )
        & uVar92
        ^ (
            (uVar66 & 0xFFFFFFB7 ^ uVar87 ^ 0x30FA3D6) & uVar38
            ^ (uVar87 ^ 0x30FA3D6) & uVar63
            ^ uVar25 & 0xFFFFFFB7
            ^ uVar87
            ^ 0x30FA3D6
        )
        & uVar68
        ^ ((uVar90 & 0xFFFFFFB7 ^ uVar87 ^ 0xFCF05C61) & uVar38 ^ (uVar90 ^ 0x4EF7ED37) & uVar20 & 0xFFFFFFB7 ^ 0x9FE170FB)
        & uVar63
        ^ (uVar20 & 0x45E8468E ^ 0x9FE170FB) & uVar90
        ^ uVar20 & 0x2CFECB21
        ^ 0xEE9F0353
    ) & 0xFFFFFFFF
    dst_dwords[0x12] = (
        (
            (uVar55 & 0x3B595CE5 ^ uVar78 & 0xD86EB7A ^ 0xE4AFA616) & uVar3
            ^ (uVar55 & 0xC06EA29A ^ 0x3EF51CB7) & uVar78
            ^ uVar55 & 0x27A0414C
        )
        * 2
        & 0xFFFFFFFF
        ^ 0xD10776C9
    ) & 0xFFFFFFFF
    dst_dwords[0x13] = (
        (
            (uVar55 & 0xFE7B5516 ^ uVar78 & 0x5868BEE ^ 0xB54B271) & uVar3
            ^ (uVar55 & 0xE395BAF9 ^ 0xF8E9E7AF) & uVar78
            ^ uVar55 & 0x1CCA2889
            ^ 0xFAECFC5
        )
        * 2
        & 0xFFFFFFFF
    ) & 0xFFFFFFFF
    dst_dwords[0x14] = (
        (
            (uVar55 & 0xC63B5145 ^ uVar78 & 0x9802EBA ^ 0xF065CD89) & uVar3
            ^ (uVar55 & 0x31E688F3 ^ 0xD71FDD4C) & uVar78
            ^ uVar55 & 0xD995B73E
            ^ 0x753001D
        )
        * 2
        & 0xFFFFFFFF
    ) & 0xFFFFFFFF
    uVar87 = (uVar64 ^ uVar41) & 0xFFFFFFFF
    dst_dwords[0x15] = (
        ((uVar26 ^ 0xCF7BBBF0) & 0x7BDDE4FF & uVar41 ^ (uVar87 & 0x8C739BB0 ^ 0xF4C4FFDF) & uVar52 ^ uVar64 ^ 0xF5A77FF9) & uVar58
        ^ ((uVar64 ^ 0x36A8090) & uVar26 ^ 0xF8B665DF) & uVar41
        ^ ((uVar64 ^ 0x8F191B20) & uVar41 ^ ~uVar41 & uVar58 ^ uVar64 ^ 0x8F191B20) & uVar28
        ^ (uVar52 ^ 0x3EFFDEB9) & uVar64
        ^ 0x48E0F769
    ) & 0xFFFFFFFF
    dst_dwords[0x16] = (
        (
            ((uVar26 ^ 0xFB9CD6BF) & 0xBEEFFFF8 ^ uVar64) & uVar41
            ^ (uVar87 & 0xE39C1007 ^ 0xE05F9926) & uVar52
            ^ uVar64
            ^ 0xDFD9CE0F
        )
        & uVar58
        ^ ((uVar52 ^ 0x5910C6BF) & uVar64 ^ (uVar64 ^ 0xBD2C76D9) & uVar26 ^ 0x856BA966) & uVar41
        ^ ((uVar64 ^ 0x5EB066DE) & uVar41 ^ uVar64 ^ 0x5EB066DE) & uVar28
        ^ (uVar52 ^ 0xE3FD38F0) & uVar64
        ^ 0xBF04BDC3
    ) & 0xFFFFFFFF
    dst_dwords[0x17] = (
        (((uVar26 ^ 0x34626D07) & 0xFF7AFFB7 ^ uVar64) & uVar41 ^ (uVar87 & 0x10A76D4F ^ 0x9F2C7F9E) & uVar52 ^ 0x66D5134F)
        & uVar58
        ^ ((uVar52 ^ 0x24C50048) & uVar64 ^ uVar26 & 0x70F1ED66 ^ 0xCF1A93F6) & uVar41
        ^ (uVar41 & 0x60568029 ^ ~uVar41 & uVar58 ^ 0x60568029) & uVar28
        ^ (uVar52 ^ 0x1226FF6F) & uVar64
        ^ 0x8255C554
    ) & 0xFFFFFFFF
    uVar87 = (uVar72 ^ uVar39 & 0xBBBDED12) & 0xFFFFFFFF
    uVar66 = (uVar12 ^ uVar39) & 0xFFFFFFFF
    dst_dwords[0x18] = (
        (
            (uVar66 & 0x4F56D2EF ^ 0x168F53DF) & uVar57
            ^ (uVar39 ^ 0x4421029) & uVar12 & 0x4F56D2EF
            ^ uVar39 & 0x5D9B9119
            ^ 0x5FB5D527
        )
        & uVar72
        ^ ((uVar12 & 0x4F56D2EF ^ uVar87 ^ 0xE2646C22) & uVar8 ^ (uVar87 ^ 0xAD32BECD) & uVar12) & uVar40
        ^ ((uVar57 ^ 0xFBBDEFD6) & uVar39 & 0x4F56D2EF ^ 0xBCED3FD3) & uVar12
        ^ (uVar57 & 0x59D98130 ^ 0xBEC37BED) & uVar39
        ^ 0x51E22A86
    ) & 0xFFFFFFFF
    dst_dwords[0x19] = (
        ((uVar12 & 0xF9EF7D3F ^ uVar39 & 0x61293C1 ^ 0xB53A104D) & uVar8 ^ (uVar39 & 0x61293C1 ^ 0x4CD56D72) & uVar12) & uVar40
        ^ (
            (uVar66 & 0xF9EF7D3F ^ 0x4AC7FEB3) & uVar57
            ^ (uVar39 ^ 0x71AD0816) & uVar12 & 0xF9EF7D3F
            ^ uVar39 & 0xC2858B9A
            ^ 0xBF56B3F3
        )
        & uVar72
        ^ ((uVar57 ^ 0x8E52F7E9) & uVar39 & 0xF9EF7D3F ^ 0x63CD6DF) & uVar12
        ^ (uVar57 & 0xB328838C ^ 0x7BEFEEB6) & uVar39
        ^ 0xD0DF58DC
    ) & 0xFFFFFFFF
    dst_dwords[0x1A] = (
        (
            (uVar12 & 0xFEBFFFD2 ^ uVar72 ^ uVar39 & 0x7148003D ^ 0x2C87FFF2) & uVar8
            ^ (uVar72 ^ uVar39 & 0x7148003D ^ 0xD2380020) & uVar12
        )
        & uVar40
        ^ (
            (uVar66 & 0xFEBFFFD2 ^ 0xA370001D) & uVar57
            ^ (uVar39 ^ 0x8B50E7ED) & uVar12 & 0xFEBFFFD2
            ^ uVar39 & 0xD7DF180F
            ^ 0x711CBB9A
        )
        & uVar72
        ^ ((uVar57 ^ 0x74AF1812) & uVar39 & 0xFEBFFFD2 ^ 0x6DFB447D) & uVar12
        ^ (uVar57 & 0x5DCFFFCF ^ 0xCB38E7E8) & uVar39
        ^ 0x5AE3AB0B
    ) & 0xFFFFFFFF
    uVar66 = (uVar73 ^ uVar4) & 0xFFFFFFFF
    uVar87 = (~uVar11 & uVar27) & 0xFFFFFFFF
    dst_dwords[0x1B] = (
        (
            (uVar11 & 0xF7BED53A ^ 0xFD77FFCF) & uVar73
            ^ (uVar66 & 0xFCF7BFF ^ 0x27C1FB3F) & uVar51
            ^ uVar4
            ^ uVar87 & 0xF7BED53A
            ^ 0x4CA880D0
        )
        & uVar9
        ^ ((uVar51 & 0xFCF7BFF ^ 0xF2B88430) & uVar4 ^ (uVar4 ^ 0xDFB055FA) & uVar11 ^ uVar87 & 0xFCF7BFF ^ 0x2E0688A1) & uVar73
        ^ ((uVar4 ^ 0xD07F2E05) & uVar11 ^ uVar4 ^ 0xD07F2E05) & uVar27
        ^ 0x97EB6E0B
    ) & 0xFFFFFFFF
    dst_dwords[0x1C] = (
        (
            (uVar11 & 0x9BFFFFF7 ^ 0xEF9FD0FB) & uVar73
            ^ (uVar66 & 0xF6F8AF3D ^ 0x296D9C41) & uVar51
            ^ uVar87 & 0x9BFFFFF7
            ^ 0xD7FE51DA
        )
        & uVar9
        ^ ((uVar51 & 0xF6F8AF3D ^ 0x19677FC6) & uVar4 ^ uVar11 & 0x446ACC8B ^ uVar87 & 0xF6F8AF3D ^ 0x490D3E6C) & uVar73
        ^ (uVar11 & 0xB29263B6 ^ 0xB29263B6) & uVar27
        ^ (uVar51 & 0xDF95337C ^ 0xAEF98C31) & uVar4
        ^ 0xCE03EE6
    ) & 0xFFFFFFFF
    dst_dwords[0x1D] = (
        (
            (uVar11 & 0x7F737EDD ^ 0xFAEDAFFF) & uVar73
            ^ (uVar66 & 0xFDFFFFE6 ^ 0xF013A395) & uVar51
            ^ uVar87 & 0x7F737EDD
            ^ 0x3D8F3E2F
        )
        & uVar9
        ^ ((uVar51 & 0xFDFFFFE6 ^ 0x7125019) & uVar4 ^ (uVar4 ^ 0x729F22AE) & uVar11 ^ uVar87 & 0xFDFFFFE6 ^ 0xB0F1E357) & uVar73
        ^ ((uVar4 ^ 0x8F60DD48) & uVar11 ^ uVar4 ^ 0x8F60DD48) & uVar27
        ^ (uVar51 & 0xDEC5C73 ^ 0x7A7F2EF4) & uVar4
        ^ 0x287856F8
    ) & 0xFFFFFFFF
    uVar87 = (uVar32 ^ uVar43) & 0xFFFFFFFF
    uVar66 = (uVar23 ^ uVar5) & 0xFFFFFFFF
    uVar41 = (uVar5 & 0xBBFEADF4) & 0xFFFFFFFF
    uVar40 = (~uVar23) & 0xFFFFFFFF
    dst_dwords[0x1E] = (
        (
            ((uVar5 ^ 0x2316A9C0) & 0xBBFEADF4 ^ uVar23) & uVar43
            ^ ((uVar23 ^ 0x99FA0CF4) & 0xFEEDF73F ^ uVar41) & uVar32
            ^ (uVar66 & 0xBBFEADF4 ^ uVar87 & 0xFEEDF73F ^ 0x59FE051B) & uVar53
            ^ (uVar41 ^ 0xE200A8EF) & uVar23
            ^ 0x5F01DA0B
        )
        & uVar1
        ^ (uVar43 & 0xFEEDF73F ^ uVar5 & 0x84055BE4 ^ 0x21FE6DD8) & uVar32
        ^ (uVar41 ^ uVar87 & 0xFEEDF73F ^ 0x59FE051B) & uVar40 & uVar53
        ^ (uVar43 & 0x3FFBF610 ^ 0x5F01DA0B) & uVar5
        ^ uVar43 & 0x86ED9FFC
        ^ 0x1E65E625
    ) & 0xFFFFFFFF
    uVar41 = (uVar5 & 0x67B7D3FF) & 0xFFFFFFFF
    dst_dwords[0x1F] = (
        (
            (uVar5 ^ 0xB1003F) & 0x67B7D3FF & uVar43
            ^ (uVar41 ^ 0x6706D3C0) & uVar32
            ^ (uVar66 & 0x67B7D3FF ^ uVar87 & 0xFFDFFFE0 ^ 0xFB40C824) & uVar53
            ^ (uVar41 ^ 0x9CF71BDB) & uVar23
            ^ 0x9E58BFC3
        )
        & uVar1
        ^ (uVar5 & 0x42E37FB ^ uVar43 & 0xFFDFFFE0 ^ 0x7DA957FF) & uVar32
        ^ (uVar41 ^ uVar87 & 0xFFDFFFE0 ^ 0xFB40C824) & uVar40 & uVar53
        ^ (uVar43 & 0x6399E404 ^ 0x9E58BFC3) & uVar5
        ^ uVar43 & 0x7936603B
        ^ 0x6A57C73D
    ) & 0xFFFFFFFF
    dst_dwords[0x20] = (
        (
            ((uVar5 ^ 0x11280B) & 0xFDFDFF6F ^ uVar23) & uVar32
            ^ ((uVar5 ^ 0xFFEED7F4) & 0xFDFDFF6F ^ uVar23) & uVar43
            ^ (uVar66 & 0xFDFDFF6F ^ uVar87 & 0x43736EDF ^ 0x3E91B3C4) & uVar53
            ^ (uVar5 & 0xFDFDFF6F ^ 0xC36C4CAB) & uVar23
            ^ 0xA6B775FC
        )
        & uVar1
        ^ (uVar43 & 0x43736EDF ^ uVar5 & 0x800E0A7F ^ 0xFFCE93B8) & uVar32
        ^ (uVar5 & 0xFDFDFF6F ^ uVar87 & 0x43736EDF ^ 0x3E91B3C4) & uVar40 & uVar53
        ^ (uVar43 & 0x7DF3F510 ^ 0xA6B775FC) & uVar5
        ^ uVar43 & 0x822C4EA3
        ^ 0x6FA144D4
    ) & 0xFFFFFFFF
    uVar87 = (uVar37 ^ uVar24) & 0xFFFFFFFF
    uVar43 = ((~uVar37 ^ uVar24) & uVar86 ^ ~uVar37 & uVar24) & 0xFFFFFFFF
    dst_dwords[0x21] = (
        ((uVar85 ^ 0x11983688) & uVar61 ^ uVar43 & 0xA2E2A4A2 ^ uVar85 ^ 0x6F1DCBDD) & uVar84
        ^ ((uVar85 ^ 0x7460DC44) & uVar87 ^ uVar85 ^ 0x7460DC44) & uVar86
        ^ (uVar37 & (uVar85 ^ 0x7460DC44) ^ uVar85 ^ 0x7460DC44) & uVar24
        ^ (uVar43 & 0xFF7FDB7F ^ uVar85 ^ 0x88FF7BEB) & uVar61
        ^ uVar85
        ^ 0x4D89219C
    ) & 0xFFFFFFFF
    dst_dwords[0x22] = (
        ((uVar85 ^ 0xFD0D5BD5) & uVar61 ^ uVar43 & 0x7D0D5B50 ^ uVar85 ^ 0x2FF7AFAE) & uVar84
        ^ (uVar37 & (uVar85 ^ 0x9CF10469) ^ uVar85 ^ 0x9CF10469) & uVar24
        ^ ((uVar85 ^ 0x9CF10469) & uVar87 ^ uVar85 ^ 0x9CF10469) & uVar86
        ^ (uVar43 & 0xDAF2BEAF ^ uVar85 ^ 0xF39CD51D) & uVar61
        ^ 0x435C6204
    ) & 0xFFFFFFFF
    dst_dwords[0x23] = (
        ((uVar85 ^ 0x4EF7ED37) & uVar61 ^ uVar43 & 0x810086F ^ 0xFDE856ED) & uVar84
        ^ (uVar37 & (uVar85 ^ 0x30FA3D6) ^ uVar85 ^ 0x30FA3D6) & uVar24
        ^ ((uVar85 ^ 0x30FA3D6) & uVar87 ^ uVar85 ^ 0x30FA3D6) & uVar86
        ^ (uVar43 & 0xF7EFF7D8 ^ 0x2CFECB21) & uVar61
        ^ 0xEE9F0353
    ) & 0xFFFFFFFF

    destination[: len(dst_dwords) * 4] = _from_uints(dst_dwords)
