"""Auto-generated from /tmp/HarpoS7/HarpoS7.Family0/Monoliths/Monolith11.cs.

DO NOT EDIT — regenerate via tools/transpile_harpo_monolith.py.

Mechanically transpiled from HarpoS7's Family-0 ``Monolith11.Execute``.
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

    uVar39 = (src_dwords[0x1A]) & 0xFFFFFFFF
    uVar24 = (src_dwords[0x14]) & 0xFFFFFFFF
    uVar26 = (src_dwords[0x13]) & 0xFFFFFFFF
    uVar66 = (src_dwords[8]) & 0xFFFFFFFF
    uVar50 = ((uVar39 & 0x25673C9B ^ 0x82100160) & uVar24 ^ ~uVar24 & uVar26 & 0x7DEFFE9F) & 0xFFFFFFFF
    uVar25 = (src_dwords[2]) & 0xFFFFFFFF
    uVar60 = (src_dwords[0x1D]) & 0xFFFFFFFF
    uVar73 = (
        ((uVar26 ^ 0xDA98C364) & 0x7DEFFE9F ^ uVar39 & 0x82100160) & uVar24 ^ ~(uVar26 & 0x25673C9B) & uVar39 & 0xA7773DFB
    ) & 0xFFFFFFFF
    uVar51 = (((uVar25 ^ uVar66) & uVar60 & 0x6F39089 ^ uVar25 & uVar66) & 0x5FFBFBAF) & 0xFFFFFFFF
    uVar61 = (src_dwords[5] & 0x104A21AB) & 0xFFFFFFFF
    uVar29 = ((uVar60 ^ uVar61) & uVar51 ^ (uVar60 & 0x4FB1DA04 ^ 0x104A21AB) & src_dwords[5]) & 0xFFFFFFFF
    uVar55 = (src_dwords[0xE]) & 0xFFFFFFFF
    uVar28 = (src_dwords[9]) & 0xFFFFFFFF
    uVar1 = (~(uVar55 & 0xFFB4B8F) & uVar60 & 0xAFFF4FDF) & 0xFFFFFFFF
    uVar30 = (((~(uVar28 & 0x6CA2D69E) ^ uVar25 & 0x6CA2D69E) & uVar39 ^ uVar25 & 0xEEB2D7FE) & 0xFDFFFE9F) & 0xFFFFFFFF
    uVar31 = (
        ~(src_dwords[1] & 0xFFBDFFF6) & uVar55 & 0x86F79499 ^ (uVar60 & 0x86B59490 ^ 0x70086866) & src_dwords[1]
    ) & 0xFFFFFFFF
    uVar24 = (
        ~(~(src_dwords[5] & 0xEFB5DE54) & uVar60 & 0x5FFBFBAF) ^ (~uVar60 & uVar51 ^ src_dwords[5]) & 0x5FFBFBAF
    ) & 0xFFFFFFFF
    uVar87 = (~((uVar60 ^ src_dwords[1] & 0x420009) & uVar55 & 0x86F79499) ^ src_dwords[1] & 0xF6BDFCF6) & 0xFFFFFFFF
    uVar18 = (src_dwords[0x17]) & 0xFFFFFFFF
    uVar88 = ((uVar66 ^ src_dwords[0x19]) & uVar18 & 0x6F39089 ^ uVar66 & src_dwords[0x19]) & 0xFFFFFFFF
    uVar89 = (uVar88 & 0x86F79499) & 0xFFFFFFFF
    uVar90 = (~((src_dwords[0x1C] & 0xF6BDFDF6 ^ uVar60) & src_dwords[0xB] & 0x7DEFFE9F) ^ uVar60 & 0x7DEFFE9F) & 0xFFFFFFFF
    uVar19 = (src_dwords[0x11]) & 0xFFFFFFFF
    uVar2 = (((uVar25 ^ uVar19 & 0x6F39089) & uVar51 ^ uVar25) & 0x86F79499) & 0xFFFFFFFF
    uVar91 = (~(src_dwords[0x14] & uVar24 & 0xA7773DFB) ^ src_dwords[5] & 0xA7773DFB) & 0xFFFFFFFF
    uVar3 = ((~(uVar18 & 0x9000) & uVar26 ^ uVar18) & 0x86F79499) & 0xFFFFFFFF
    uVar66 = (~uVar66) & 0xFFFFFFFF
    uVar92 = (~((uVar39 & 0x82100160 ^ 0x7DEFFE9F) & src_dwords[0x14]) ^ uVar26 & uVar39 & 0x25673C9B) & 0xFFFFFFFF
    uVar93 = (
        ~((~src_dwords[5] ^ uVar25 & 0xFFB5FE74) & uVar39 & 0x104A21AB) ^ (src_dwords[5] & 0x4A018B ^ 0xAFB54E54) & uVar25
    ) & 0xFFFFFFFF
    uVar48 = (
        (uVar19 & 0x82100140 ^ 0x2DEF4E9F) & src_dwords[5] ^ (src_dwords[5] & 0x2DEF4E9F ^ uVar19) & src_dwords[0xD] & 0xAFFF4FDF
    ) & 0xFFFFFFFF
    uVar4 = ((uVar60 & 0x6F39089 ^ uVar66) & uVar25 ^ src_dwords[8]) & 0xFFFFFFFF
    uVar62 = (~uVar61 & uVar60 ^ src_dwords[5] & uVar51 & 0x104A21AB) & 0xFFFFFFFF
    uVar63 = (uVar62 & 0x5FFBFBAF) & 0xFFFFFFFF
    uVar64 = (~uVar25) & 0xFFFFFFFF
    uVar49 = ((uVar64 & 0x6CA2D69E ^ uVar28 & 0x80100000) & uVar39 ^ uVar25 & uVar28 & 0xECB2D69E) & 0xFFFFFFFF
    uVar47 = (
        ((uVar28 & 0xDFDFFF77 ^ uVar66) & src_dwords[0x16] & 0xAFFF6FDF ^ ~(src_dwords[8] & 0xAFFF6FDF) & src_dwords[9])
        & 0xFFFFDFFF
    ) & 0xFFFFFFFF
    uVar67 = (uVar66 & src_dwords[0x19] & 0x86F79499 ^ uVar18 & 0x5FFBFBAF) & 0xFFFFFFFF
    uVar68 = (
        (~(src_dwords[0xB] & 0xFFFFDF77) ^ src_dwords[4] & 0x2088) & src_dwords[0x14] & 0x104A21AB
        ^ (src_dwords[0xB] ^ 0xEFB5FEDC) & src_dwords[4] & 0xDFDFDF77
    ) & 0xFFFFFFFF
    uVar69 = ((~(uVar19 & 0x8FF79799) & uVar24 ^ src_dwords[0x16] & uVar19 & 0x8FF79799) & 0xF6BDFCF6) & 0xFFFFFFFF
    uVar5 = (~src_dwords[0xD]) & 0xFFFFFFFF
    uVar70 = (~((src_dwords[5] & 0xD210B160 ^ uVar5) & uVar19 & 0xAFFF4FDF) ^ src_dwords[5] & 0x7DEFFE9F) & 0xFFFFFFFF
    uVar6 = ((uVar60 & src_dwords[0x1C] & 0xF6BDFDF6 ^ src_dwords[0xB]) & 0x7DEFFE9F) & 0xFFFFFFFF
    uVar23 = ((uVar25 & 0xFFB5FE74 ^ src_dwords[5]) & uVar39 & 0x104A21AB ^ uVar25 & 0xAFFF4FDF) & 0xFFFFFFFF
    uVar7 = (~(uVar26 & 0x9000) & uVar18 & 0xAFFFDFDF) & 0xFFFFFFFF
    uVar106 = ((~(uVar19 & 0x6F39089) & uVar51 ^ uVar25) & 0x86F79499 ^ uVar19 & 0x5FFBFBAF) & 0xFFFFFFFF
    uVar8 = (
        ((src_dwords[1] & 0x420009 ^ ~uVar60) & uVar55 ^ uVar60) & 0x86F79499 ^ (uVar60 & 0x86B59490 ^ 0x420009) & src_dwords[1]
    ) & 0xFFFFFFFF
    uVar52 = (~(~(uVar25 & 0x6F39089) & uVar19 & 0x5FFBFBAF) ^ uVar25 & uVar51 & 0x86F79499) & 0xFFFFFFFF
    uVar53 = (~(src_dwords[0x16] & uVar24 & 0xF6BDFCF6) ^ uVar19 & 0x86F79499) & 0xFFFFFFFF
    uVar54 = (~(~src_dwords[7] & src_dwords[0x18] & 0xF6BDFCF6) ^ uVar5 & src_dwords[7] & 0xF6BDFCF6) & 0xFFFFFFFF
    uVar9 = (~uVar87 & uVar55 & 0xAFFF4FDF ^ src_dwords[0x19] & 0xDFDFDF77) & 0xFFFFFFFF
    uVar10 = (
        ((uVar62 & 0x4250A323 ^ 0x9DAF5C9C) & uVar24 ^ 0x62400022) & uVar29
        ^ (uVar62 & 0x1DAB588C ^ 0x10A341) & uVar24
        ^ uVar63
        ^ 0x9DAF5C9C
    ) & 0xFFFFFFFF
    uVar62 = (~(uVar60 & ~(uVar25 & 0x6F39089) & 0x86F79499) ^ src_dwords[8] & 0x5FFBFBAF) & 0xFFFFFFFF
    uVar32 = (
        (src_dwords[9] & 0x20200088 ^ ~src_dwords[0x16]) & src_dwords[8] & 0xAFFF4FDF
        ^ (src_dwords[0x16] & 0x8FDF4F57 ^ 0x50009020) & src_dwords[9]
    ) & 0xFFFFFFFF
    uVar33 = (~(uVar25 & 0x5FDBDB27) & src_dwords[0x14] & 0xDFDFDF77) & 0xFFFFFFFF
    uVar27 = ((src_dwords[0x14] & 0xDFDFDF77 ^ uVar64 & 0x202088) & uVar26 ^ uVar25 & 0x5FFBFBAF ^ uVar33) & 0xFFFFFFFF
    uVar11 = (~((src_dwords[0x19] & 0xDFDFFF77 ^ uVar55) & uVar87 & 0xAFFF4FDF) ^ src_dwords[0x19] & 0xDFDFDF77) & 0xFFFFFFFF
    uVar12 = (
        ~(~(uVar19 & 0x2DEF4E9F) & src_dwords[5] & 0xFFFFFFDF) ^ ~(src_dwords[5] & 0x2DEF4E9F) & src_dwords[0xD] & 0xAFFF4FDF
    ) & 0xFFFFFFFF
    uVar34 = (~(uVar60 & 0x74ADFC96) & src_dwords[0x1C] & 0xF6BDFCF6 ^ uVar60 & src_dwords[0xB] & 0x7DEFFE9F) & 0xFFFFFFFF
    uVar94 = (((uVar19 & 0x8FF79799 ^ src_dwords[0x16]) & uVar24 ^ src_dwords[0x16]) & 0xF6BDFCF6) & 0xFFFFFFFF
    uVar19 = (src_dwords[9]) & 0xFFFFFFFF
    uVar13 = (
        (src_dwords[8] & 0x8FDF4F57 ^ 0x20200088) & uVar19 ^ ~(uVar28 & 0xDFDFFF77) & src_dwords[0x16] & 0xAFFF4FDF
    ) & 0xFFFFFFFF
    uVar14 = (uVar92 ^ 0xC6D87455) & 0xFFFFFFFF
    uVar95 = ((~uVar94 ^ uVar53) & uVar69 ^ uVar53) & 0xFFFFFFFF
    uVar95 = (
        (uVar14 & uVar73 ^ uVar95 & 0x39278BAA ^ uVar92 ^ 0xF6DCF55F) & uVar50
        ^ (uVar95 ^ uVar92 ^ 0xF614C50F) & uVar73
        ^ uVar92
        ^ 0xC6D87455
    ) & 0xFFFFFFFF
    uVar35 = (
        (
            (src_dwords[0x14] & 0x104A0123 ^ ~src_dwords[4]) & src_dwords[0xB] & 0xFFFFDF77
            ^ ~(src_dwords[0x14] & 0x104A21AB) & src_dwords[4]
        )
        & 0xDFDFFFFF
    ) & 0xFFFFFFFF
    uVar74 = ((uVar26 & 0x86F79499 ^ 0xAFFF4FDF) & uVar18) & 0xFFFFFFFF
    uVar36 = ((~(uVar50 & 0xAF773FFB) ^ uVar19 & 0x5088C004) & src_dwords[0x10] & 0xF6BDFCF6 ^ uVar19 & 0xA7773DFB) & 0xFFFFFFFF
    uVar64 = ((uVar28 & 0x80100000 ^ 0x7DEFFE9F) & uVar39 ^ ~(uVar64 & uVar19 & 0xECB2D69E)) & 0xFFFFFFFF
    uVar28 = (
        (~(uVar4 & 0x1DEBF98E) & 0xEF73EFE7 ^ uVar62 & 0x30CCB15A) & uVar51
        ^ (uVar4 & 0x4F334AA5 ^ 0x9DAF5C9C) & uVar62
        ^ (uVar4 & 0x5FFBFBAF ^ 0x9DAF5C9C) & 0xEF73EFE7
    ) & 0xFFFFFFFF
    uVar96 = (
        ((uVar106 & 0x30CCB15A ^ 0x9DAF5C9C) & uVar2 ^ uVar106 & 0x6250A363 ^ 0x9DAF5C9C) & uVar52
        ^ (~(uVar106 & 0xDFBF5EBD) & uVar2 ^ uVar106 ^ 0x108C1018) & 0x72DCB37B
    ) & 0xFFFFFFFF
    uVar37 = (
        ~((src_dwords[0x10] & 0xFEBDFEF6 ^ ~uVar19) & uVar50 & 0xA7773DFB)
        ^ ~(src_dwords[0x10] & 0x5088C004) & uVar19 & 0xF7FFFDFF
    ) & 0xFFFFFFFF
    uVar38 = (uVar74 ^ uVar7) & 0xFFFFFFFF
    uVar71 = (
        ((uVar53 ^ uVar7) & uVar74 ^ uVar53 ^ uVar7) & uVar94
        ^ ~((uVar74 ^ uVar94) & uVar53) & uVar69
        ^ (uVar38 & uVar94 ^ ~uVar7 & uVar74) & uVar3
        ^ uVar74
    ) & 0xFFFFFFFF
    uVar15 = ((~src_dwords[0x18] & src_dwords[0xD] ^ src_dwords[7]) & 0xF6BDFCF6) & 0xFFFFFFFF
    uVar16 = (~uVar23) & 0xFFFFFFFF
    uVar61 = (((uVar39 ^ src_dwords[5]) & 0x4A018B ^ 0x10002020) & uVar25 ^ uVar61) & 0xFFFFFFFF
    uVar39 = ((uVar23 ^ uVar93 ^ uVar31) & uVar61) & 0xFFFFFFFF
    uVar75 = (
        (~uVar39 ^ uVar93 ^ uVar31) & uVar87 ^ (uVar61 ^ uVar87) & uVar8 & uVar31 ^ uVar16 & uVar61 ^ uVar23 ^ uVar93
    ) & 0xFFFFFFFF
    uVar76 = (uVar55 & 0x5FFBFBAF) & 0xFFFFFFFF
    uVar97 = (~((src_dwords[7] ^ src_dwords[0xD]) & src_dwords[0x18] & 0xF6BDFCF6) ^ src_dwords[7] & 0xF6BDFCF6) & 0xFFFFFFFF
    uVar77 = ((uVar54 ^ uVar47) & uVar97) & 0xFFFFFFFF
    uVar17 = (~uVar97) & 0xFFFFFFFF
    uVar98 = (
        (~((uVar97 ^ uVar47) & uVar13) ^ uVar17 & uVar47) & uVar32
        ^ (~((uVar17 ^ uVar13) & uVar54) ^ uVar97 ^ uVar13) & uVar15
        ^ (uVar77 ^ uVar54) & uVar13
        ^ uVar17 & uVar54
        ^ uVar97
    ) & 0xFFFFFFFF
    uVar78 = (~(uVar19 & 0xAF773FFB) & src_dwords[0x10] & 0xF6BDFCF6 ^ (uVar50 ^ 0xFEBDFEF6) & uVar19 & 0xA7773DFB) & 0xFFFFFFFF
    uVar18 = (((uVar18 & 0x6F39089 ^ uVar66) & src_dwords[0x19] ^ src_dwords[8]) & 0x86F79499) & 0xFFFFFFFF
    uVar55 = (
        ~(uVar55 & 0xAFFF6FDF) & src_dwords[0x19] & 0xDFDFDF77 ^ ~(src_dwords[0x19] & 0xDFDFFF77) & uVar87 & 0xAFFF4FDF
    ) & 0xFFFFFFFF
    uVar56 = (
        ~(((uVar16 ^ uVar93) & uVar31 ^ uVar39 ^ uVar23) & uVar87)
        ^ (uVar61 ^ uVar23 ^ uVar93 ^ uVar87) & uVar8 & uVar31
        ^ (uVar61 ^ uVar93) & uVar23
        ^ uVar93
    ) & 0xFFFFFFFF
    uVar66 = (uVar8 ^ uVar31 ^ 0xCF334EA5) & 0xFFFFFFFF
    uVar39 = (~uVar31 & uVar8) & 0xFFFFFFFF
    uVar19 = (
        ((uVar66 & uVar74 ^ uVar8 ^ uVar31 ^ 0xCF334EA5) & uVar7 ^ (uVar39 ^ uVar31) & 0xCF334EA5) & uVar87
        ^ (~(~uVar74 & uVar31) & 0xCF334EA5 ^ (uVar8 ^ 0xCF334EA5) & uVar74 ^ uVar8) & uVar7
        ^ (uVar66 & uVar87 ^ ~uVar31 & 0xCF334EA5 ^ uVar8) & uVar74 & uVar3
        ^ uVar39 & 0xCF334EA5
        ^ 0x30CCB15A
    ) & 0xFFFFFFFF
    uVar20 = (uVar78 ^ uVar37) & 0xFFFFFFFF
    uVar57 = (
        (uVar24 & 0x7FCA4832 ^ 0x10A341) & uVar29 ^ ~uVar24 & uVar63 & 0xE26514AE ^ ~(uVar24 & 0x10A341) & 0x9DBFFFDD
    ) & 0xFFFFFFFF
    uVar79 = (~uVar78) & 0xFFFFFFFF
    uVar21 = (uVar60 & 0xAFFF4FDF) & 0xFFFFFFFF
    uVar99 = (
        (~((uVar20 ^ uVar48) & uVar36) ^ uVar20 & uVar48 ^ uVar37) & uVar70
        ^ (~((uVar79 ^ uVar37 ^ uVar36) & uVar70) ^ uVar78 ^ uVar37 ^ uVar36) & uVar12
        ^ (uVar37 ^ uVar36) & uVar78
        ^ uVar36
    ) & 0xFFFFFFFF
    uVar40 = (~uVar21) & 0xFFFFFFFF
    uVar39 = ((uVar40 ^ uVar1) & uVar34) & 0xFFFFFFFF
    uVar66 = ((uVar21 ^ uVar1) & uVar76) & 0xFFFFFFFF
    uVar22 = (
        ~((~((uVar40 ^ uVar34 ^ uVar1) & uVar6) ^ uVar66 ^ uVar21 ^ uVar34 ^ uVar1) & uVar90)
        ^ (uVar39 ^ uVar66 ^ uVar21 ^ uVar1) & uVar6
        ^ uVar39
        ^ uVar1
    ) & 0xFFFFFFFF
    uVar100 = (
        (~((uVar74 ^ uVar69) & uVar53) ^ uVar74 ^ uVar69) & uVar94
        ^ ((~uVar53 ^ uVar7) & uVar74 ^ uVar53 ^ uVar7) & uVar69
        ^ ~((uVar38 & uVar69 ^ ~uVar7 & uVar74) & uVar3)
    ) & 0xFFFFFFFF
    uVar41 = (
        (src_dwords[0xB] & 0x104A0123 ^ src_dwords[4] & 0x2088) & src_dwords[0x14] ^ src_dwords[4] & 0xDFDFDF77
    ) & 0xFFFFFFFF
    uVar42 = (uVar11 ^ uVar9) & 0xFFFFFFFF
    uVar39 = (~uVar92 & uVar50) & 0xFFFFFFFF
    uVar65 = (((uVar42 ^ uVar92) & uVar73 ^ uVar39 ^ uVar9 ^ uVar92) & uVar55 ^ (~uVar39 ^ uVar11) & uVar73 ^ uVar92) & 0xFFFFFFFF
    uVar39 = ((~uVar61 ^ uVar93) & uVar23) & 0xFFFFFFFF
    uVar58 = (~uVar70 ^ uVar48) & 0xFFFFFFFF
    uVar43 = (
        ((uVar36 ^ 0x104A21AB) & uVar23 ^ uVar16 & uVar61 & 0xE26514AE ^ uVar36 ^ 0x104A21AB) & uVar93
        ^ ((uVar39 ^ uVar93 ^ 0xE26514AE) & (uVar37 ^ uVar36) ^ uVar39 ^ uVar93 ^ 0xE26514AE) & uVar78
        ^ ((uVar36 ^ 0xF22F3505) & uVar61 ^ uVar36 ^ 0xF22F3505) & uVar23
        ^ (uVar36 ^ 0x4000AA) & 0xE26514AE
    ) & 0xFFFFFFFF
    uVar72 = (uVar70 ^ uVar48) & 0xFFFFFFFF
    uVar59 = (uVar58 & uVar12 ^ uVar70) & 0xFFFFFFFF
    uVar44 = (
        (
            (~(uVar58 & uVar1) ^ uVar58 & uVar21 ^ uVar70 ^ uVar48) & uVar12
            ^ (uVar60 & 0x86D84455 ^ uVar70) & uVar1
            ^ (uVar70 ^ 0x39278BAA) & uVar21
            ^ uVar70
            ^ 0x19270888
        )
        & uVar76
        ^ ((uVar21 ^ 0x6250A363) & uVar72 ^ uVar21 ^ 0x6250A363) & uVar12
        ^ ((uVar59 ^ 0x39278BAA) & uVar21 ^ 0x9DAF5C9C) & uVar1
        ^ (uVar21 ^ 0x6250A363) & uVar70
        ^ uVar60 & 0x29270B8A
        ^ 0xDFFF7CDD
    ) & 0xFFFFFFFF
    uVar39 = (
        (~((~uVar76 ^ uVar34 ^ uVar90) & uVar6) ^ uVar76 ^ uVar34 ^ uVar90) & uVar21
        ^ ~((uVar21 ^ uVar6) & uVar76) & uVar1
        ^ uVar90
    ) & 0xFFFFFFFF
    uVar101 = (
        (~(~uVar6 & uVar34) ^ uVar40 & uVar76 ^ uVar21) & uVar1
        ^ ((~uVar34 ^ uVar1) & uVar6 ^ uVar66 ^ uVar21 ^ uVar34 ^ uVar1) & uVar90
        ^ uVar21
        ^ uVar6
    ) & 0xFFFFFFFF
    uVar45 = ((src_dwords[0x14] & src_dwords[5] ^ ~src_dwords[5] & uVar24) & 0xA7773DFB) & 0xFFFFFFFF
    uVar102 = (uVar94 ^ uVar53) & 0xFFFFFFFF
    uVar46 = ((uVar34 ^ uVar6) & uVar90 ^ (uVar32 ^ uVar47) & uVar13 ^ uVar34 ^ uVar47) & 0xFFFFFFFF
    uVar66 = (uVar92 ^ uVar73 ^ 0xC6D87455) & 0xFFFFFFFF
    uVar60 = ((uVar73 ^ 0x30CCB15A) & uVar92) & 0xFFFFFFFF
    uVar80 = (uVar92 ^ uVar73 ^ 0x39278BAA) & 0xFFFFFFFF
    uVar80 = (
        ((uVar66 & uVar102 ^ uVar92 ^ uVar73 ^ 0xC6D87455) & uVar69 ^ (uVar73 ^ 0xC83050) & 0x9EB3AF0 ^ uVar66 & uVar53 ^ uVar60)
        & uVar50
        ^ (uVar80 & uVar102 ^ uVar92 ^ uVar73 ^ 0x39278BAA) & uVar69
        ^ uVar80 & uVar53
        ^ uVar73 & 0x9EB3AF0
        ^ uVar60
        ^ 0x3004810A
    ) & 0xFFFFFFFF
    uVar6 = (~(((uVar34 ^ uVar32 ^ uVar6 ^ uVar47) & uVar13 ^ uVar6 ^ uVar47) & uVar90) ^ (uVar34 ^ uVar32) & uVar13) & 0xFFFFFFFF
    uVar81 = (
        ((uVar24 & 0x6250A363 ^ 0x9DAF5C9C) & uVar63 ^ uVar24 & 0x7FCA4832 ^ 0x9DBFFFDD) & uVar29
        ^ (uVar24 & 0x1D9AEB51 ^ 0xE26514AE) & uVar63
        ^ ~(uVar24 & 0xE26514AE) & 0x7FDAEB73
    ) & 0xFFFFFFFF
    uVar16 = (uVar16 & uVar93) & 0xFFFFFFFF
    uVar29 = (
        ((~uVar37 & uVar78 ^ uVar79 & uVar36 ^ uVar16 ^ uVar23 ^ 0xFFBFFF55) & uVar61 ^ (uVar36 ^ 0x4000AA) & uVar23) & 0xE26514AE
        ^ (~((~uVar37 ^ uVar36) & uVar23 & 0xE26514AE) ^ uVar37 ^ uVar36) & uVar78
        ^ uVar36
        ^ 0x104A21AB
    ) & 0xFFFFFFFF
    uVar60 = (
        ~(((uVar94 ^ uVar69) & uVar38 ^ uVar74 ^ uVar7) & uVar3)
        ^ (~((~uVar94 ^ uVar69) & uVar74) ^ uVar94 ^ uVar69) & uVar7
        ^ uVar74
        ^ uVar94
    ) & 0xFFFFFFFF
    uVar66 = (uVar21 ^ uVar1 ^ 0xC6D87455) & 0xFFFFFFFF
    uVar34 = (~uVar92 ^ uVar73) & 0xFFFFFFFF
    uVar66 = (
        (
            (uVar66 & uVar72 ^ uVar21 ^ uVar1 ^ 0xC6D87455) & uVar12
            ^ ~(~uVar1 & uVar21 & 0xDFFF7CDD) & 0xE6D8F777
            ^ uVar66 & uVar70
            ^ uVar1
        )
        & uVar76
        ^ ((~(uVar58 & uVar21) ^ uVar70 ^ uVar48) & uVar1 ^ (uVar21 ^ 0x9DAF5C9C) & uVar72 ^ uVar21 ^ 0x9DAF5C9C) & uVar12
        ^ ((uVar70 ^ 0xC6D87455) & uVar21 ^ uVar70 ^ 0x5B7728C9) & uVar1
        ^ (uVar21 ^ 0x9DAF5C9C) & uVar70
        ^ (uVar21 ^ 0xBDAFDFBE) & 0xC6D87455
    ) & 0xFFFFFFFF
    uVar38 = ((uVar17 ^ uVar15) & uVar54 ^ uVar97 ^ uVar15) & 0xFFFFFFFF
    uVar103 = (
        (
            (~(uVar34 & uVar94) ^ uVar34 & uVar53 ^ uVar92 ^ uVar73) & uVar69
            ^ (uVar53 ^ uVar73 ^ 0xCF334EA5) & uVar92
            ^ (uVar53 ^ 0xF614C50F) & uVar73
            ^ uVar53
            ^ 0xCF334EA5
        )
        & uVar50
        ^ (uVar102 & uVar14 ^ uVar92 ^ 0xC6D87455) & uVar69
        ^ (uVar73 ^ 0xCF334EA5) & uVar92
        ^ uVar14 & uVar53
        ^ uVar73 & 0x39278BAA
        ^ 0xC6104405
    ) & 0xFFFFFFFF
    uVar53 = ((uVar32 ^ uVar47 ^ uVar38) & uVar13 ^ (uVar47 ^ uVar38) & uVar32 ^ uVar97) & 0xFFFFFFFF
    uVar14 = ((~uVar35 ^ uVar68) & uVar41 ^ uVar68 ^ 0x1D9AEB51) & 0xFFFFFFFF
    uVar90 = (uVar13 ^ uVar90) & 0xFFFFFFFF
    uVar34 = ((uVar49 ^ 0xC6D87455) & uVar68) & 0xFFFFFFFF
    uVar58 = (
        (~(uVar40 & uVar1 & 0xDFFF7CDD) & 0xE6D8F777 ^ uVar59 & 0x39278BAA ^ uVar21) & uVar76
        ^ (uVar58 & uVar12 ^ uVar21 ^ uVar70 ^ 0xA488D736) & uVar1
        ^ uVar21
        ^ 0x9DAF5C9C
    ) & 0xFFFFFFFF
    uVar76 = (
        (~(uVar64 & uVar14) ^ uVar14 & uVar49) & uVar30
        ^ (uVar35 & (uVar49 ^ 0x39278BAA) ^ uVar34 ^ uVar49 ^ 0xDB429F04) & uVar41
        ^ uVar49 & 0x1D9AEB51
        ^ uVar34
        ^ 0xFB679FAE
    ) & 0xFFFFFFFF
    uVar82 = (
        (uVar4 & 0x52981229 ^ 0x6250A363) & uVar62
        ^ (uVar4 & 0x1DEBF98E ^ ~(uVar62 & 0xBDEFFDDE)) & uVar51 & 0xEF73EFE7
        ^ ~(uVar4 & 0x10881008) & 0xBDEFFDDE
    ) & 0xFFFFFFFF
    uVar104 = (
        (~(uVar67 & 0x30CCB15A) & 0xBDEFFDDE ^ uVar88 & 0x86330481) & uVar18
        ^ ~((uVar67 ^ 0xDFBF5EBD) & uVar89 & 0xEF73EFE7) & 0x72DCB37B
        ^ uVar67 & 0xCF334EA5
    ) & 0xFFFFFFFF
    uVar1 = ((uVar101 & uVar39 ^ uVar22) & 0xA258DB45) & 0xFFFFFFFF
    uVar105 = (
        (~(uVar62 & 0xDFBF5EBD) ^ uVar4 & 0x5FBB5AAD) & uVar51 & 0xBDEFFDDE
        ^ (~(uVar62 & 0xBDEFFDDE) & uVar4 & 0x5FFBFBAF ^ 0xBDEFFDDE) & 0xDFBF5EBD
    ) & 0xFFFFFFFF
    uVar62 = ((uVar7 ^ uVar3) & uVar74) & 0xFFFFFFFF
    uVar4 = ((uVar8 ^ 0x30CCB15A) & uVar74) & 0xFFFFFFFF
    uVar38 = (
        ((uVar31 & 0xCF334EA5 ^ uVar62 ^ uVar7 ^ 0x30CCB15A) & uVar8 ^ (uVar62 ^ uVar7 ^ 0x30CCB15A) & uVar31 ^ 0xCF334EA5)
        & uVar87
        ^ (uVar31 & 0xCF334EA5 ^ 0x30CCB15A) & ~uVar8
        ^ (uVar8 ^ uVar4 ^ 0x30CCB15A) & uVar7
        ^ uVar4 & uVar3
    ) & 0xFFFFFFFF
    uVar4 = ((~uVar90 & uVar46 & 0x39278BAA ^ 0xC6D87455) & uVar6 ^ uVar90) & 0xFFFFFFFF
    uVar7 = (~uVar74 & uVar7) & 0xFFFFFFFF
    uVar94 = (
        ((uVar46 & 0x39278BAA ^ 0xC6D87455) & uVar6 ^ uVar46) & uVar90 ^ ~(uVar46 & 0x39278BAA) & uVar6 ^ uVar46 ^ 0xC6D87455
    ) & 0xFFFFFFFF
    uVar102 = (
        ((~(~uVar87 & uVar8) ^ uVar7) & 0xCF334EA5 ^ uVar87) & uVar31
        ^ (~uVar7 & 0xCF334EA5 ^ uVar8) & uVar87
        ^ (uVar87 ^ uVar31) & uVar74 & uVar3 & 0xCF334EA5
        ^ uVar8
        ^ 0x30CCB15A
    ) & 0xFFFFFFFF
    uVar14 = (
        (~uVar47 & uVar32 ^ ~((uVar32 ^ uVar47) & uVar97)) & uVar13
        ^ ((uVar97 ^ uVar32) & uVar54 ^ uVar97 ^ uVar32) & uVar15
        ^ (~uVar77 ^ uVar54 ^ uVar47) & uVar32
    ) & 0xFFFFFFFF
    uVar47 = (uVar98 & 0x5DA724BA) & 0xFFFFFFFF
    uVar3 = ((~(uVar53 & 0x5DA724BA) ^ uVar47) & uVar14 ^ uVar47) & 0xFFFFFFFF
    uVar87 = (
        ((uVar8 ^ uVar87) & uVar23 ^ uVar8 ^ uVar87) & uVar31 ^ ((uVar8 ^ uVar87) & uVar31 ^ uVar23) & uVar93 ^ uVar61 ^ uVar87
    ) & 0xFFFFFFFF
    uVar59 = (
        ((uVar64 ^ uVar35 ^ uVar68 ^ uVar49) & uVar30 ^ uVar35 ^ uVar49 ^ 0x24BD60FB) & uVar41
        ^ (uVar68 ^ uVar49 ^ 0xDB429F04) & uVar30
        ^ uVar49
        ^ 0x39278BAA
    ) & 0xFFFFFFFF
    uVar8 = ((~uVar98 & uVar14 & 0xA258DB45 ^ 0x5DA724BA) & uVar53 ^ (uVar47 ^ 0xA258DB45) & uVar14) & 0xFFFFFFFF
    uVar62 = (
        (~uVar106 & ~uVar2 & uVar52 & 0xEF73EFE7 ^ uVar106) & 0x72DCB37B
        ^ (uVar106 & 0xCF334EA5 ^ 0xAD63EDC6) & uVar2
        ^ 0xBDEFFDDE
    ) & 0xFFFFFFFF
    uVar2 = (
        ((uVar52 & 0x30CCB15A ^ 0x9DAF5C9C) & uVar106 ^ 0xDFBF5EBD) & uVar2
        ^ (~(uVar52 & 0xDFBF5EBD) & uVar106 ^ 0x6250A363) & 0xEF73EFE7
    ) & 0xFFFFFFFF
    uVar13 = (
        ~(uVar67 & 0xDFBF5EBD) & uVar18 & 0xBDEFFDDE ^ (uVar67 & 0x30CCB15A ^ 0x42100221) & uVar89 ^ 0xCF334EA5
    ) & 0xFFFFFFFF
    uVar63 = (
        ~(((uVar42 ^ uVar73 ^ uVar50) & uVar92 ^ uVar11 ^ uVar73 ^ uVar50) & uVar55)
        ^ (~uVar11 ^ uVar73 ^ uVar50) & uVar92
        ^ uVar11
        ^ uVar50
    ) & 0xFFFFFFFF
    uVar106 = ((uVar93 ^ 0x1D9AEB51) & uVar23) & 0xFFFFFFFF
    uVar47 = (uVar106 ^ uVar93 ^ 0xE26514AE) & 0xFFFFFFFF
    uVar31 = (
        ((uVar78 & (uVar23 ^ 0xE26514AE) ^ uVar23 ^ 0xE26514AE) & uVar61 ^ uVar78 & uVar47 ^ uVar106 ^ uVar93 ^ 0xE26514AE)
        & uVar36
        ^ (
            (uVar37 & (uVar23 ^ 0xE26514AE) ^ uVar23 ^ 0xE26514AE) & uVar78
            ^ (uVar16 ^ 0x4000AA) & 0xE26514AE
            ^ uVar23 & 0xDD0CAFA
        )
        & uVar61
        ^ (uVar37 & uVar47 ^ uVar106 ^ uVar93 ^ 0xE26514AE) & uVar78
        ^ ~(uVar23 & 0xD90CA50) & 0x1DDAEBFB
        ^ uVar16 & 0xEFB5DE54
    ) & 0xFFFFFFFF
    uVar32 = ((~uVar39 & uVar101 ^ ~uVar22 & uVar39) & 0xA258DB45) & 0xFFFFFFFF
    uVar98 = (
        ((uVar98 & 0xA258DB45 ^ 0x5DA724BA) & uVar14 ^ uVar98 & 0xA258DB45 ^ 0x5DA724BA) & uVar53
        ^ ~(~uVar98 & uVar14) & 0xA258DB45
        ^ uVar98
    ) & 0xFFFFFFFF
    uVar40 = (
        ~(
            (~(((uVar58 ^ src_dwords[0xD]) & uVar44 ^ uVar58 ^ src_dwords[0xD]) & uVar66) ^ ~uVar44 & src_dwords[0xD])
            & src_dwords[4]
        )
        ^ uVar66
    ) & 0xFFFFFFFF
    uVar47 = (~uVar55 ^ uVar97) & 0xFFFFFFFF
    uVar90 = ((~uVar46 & uVar90 ^ uVar46 ^ 0x39278BAA) & uVar6 ^ uVar90) & 0xFFFFFFFF
    uVar77 = (
        (~(uVar47 & uVar9) ^ uVar55 ^ uVar97) & uVar11
        ^ (uVar15 ^ uVar9) & uVar55 & uVar97
        ^ uVar47 & uVar15 & uVar54
        ^ uVar97
        ^ uVar15
    ) & 0xFFFFFFFF
    uVar106 = (~uVar80 ^ uVar95) & 0xFFFFFFFF
    uVar93 = (~uVar2) & 0xFFFFFFFF
    uVar83 = (~(uVar2 & uVar106) ^ uVar106 & uVar96 ^ uVar80 ^ uVar95) & 0xFFFFFFFF
    uVar107 = (~(uVar103 & uVar106) ^ uVar95) & 0xFFFFFFFF
    uVar23 = ((uVar93 ^ uVar96) & uVar95) & 0xFFFFFFFF
    uVar46 = (~uVar95) & 0xFFFFFFFF
    uVar84 = (
        (
            ~(((~(uVar103 & uVar83) ^ uVar2 ^ uVar23 ^ uVar96) & uVar62 ^ uVar107 & uVar96) & src_dwords[0x10])
            ^ uVar103 & uVar46
            ^ uVar95
        )
        & uVar26
        ^ uVar103
        ^ src_dwords[0x10]
    ) & 0xFFFFFFFF
    uVar108 = (~((src_dwords[0x14] ^ src_dwords[5]) & uVar24 & 0xA7773DFB) ^ src_dwords[0x14] & 0xA7773DFB) & 0xFFFFFFFF
    uVar51 = (
        (~((uVar45 ^ uVar91) & uVar35) ^ uVar45 ^ uVar91) & uVar68
        ^ (uVar35 ^ uVar68) & uVar41 & (uVar45 ^ uVar91)
        ^ uVar108 & uVar45 & ~uVar91
        ^ uVar91
    ) & 0xFFFFFFFF
    uVar69 = ((~uVar98 ^ uVar8) & uVar3) & 0xFFFFFFFF
    uVar85 = ((~(uVar98 & ~src_dwords[6]) ^ src_dwords[6]) & uVar8 ^ uVar98 ^ uVar69) & 0xFFFFFFFF
    uVar86 = ((~(~uVar4 & src_dwords[10]) ^ uVar90) & uVar94 ^ (uVar4 ^ ~uVar90) & src_dwords[10] ^ uVar90) & 0xFFFFFFFF
    uVar6 = (~((~(uVar100 & 0xA258DB45) & uVar71 ^ 0xA258DB45) & uVar60) ^ uVar71) & 0xFFFFFFFF
    uVar52 = (~uVar57 & uVar10) & 0xFFFFFFFF
    uVar53 = (
        ((uVar88 & 0x84638480 ^ 0x30CCB15A) & uVar67 ^ uVar89 ^ 0x42100221) & uVar18
        ^ (uVar88 & 0x2508001 ^ 0x30CCB15A) & uVar67
        ^ uVar89
        ^ 0x2040A142
    ) & 0xFFFFFFFF
    uVar14 = (~((uVar57 ^ uVar10) & uVar81) ^ uVar57 ^ uVar52) & 0xFFFFFFFF
    uVar16 = (uVar53 & uVar14) & 0xFFFFFFFF
    uVar21 = (uVar13 ^ uVar104) & 0xFFFFFFFF
    uVar74 = (uVar13 & ~uVar104) & 0xFFFFFFFF
    uVar18 = (
        ((uVar57 & uVar21 ^ uVar104 ^ uVar74) & uVar53 ^ uVar57 & uVar13 & uVar104) & src_dwords[0x16]
        ^ ((~(uVar81 & ~uVar57) ^ uVar57) & uVar10 ^ ~uVar16 ^ uVar57) & src_dwords[0x1C]
        ^ uVar53
        ^ uVar57
    ) & 0xFFFFFFFF
    uVar34 = (uVar87 & uVar75 & 0xA258DB45 ^ uVar56) & 0xFFFFFFFF
    uVar24 = ((uVar17 ^ uVar15) & uVar9) & 0xFFFFFFFF
    uVar61 = (
        (~uVar24 ^ uVar97 ^ uVar15) & uVar11 ^ (uVar24 ^ uVar97 ^ uVar15) & uVar55 ^ ~(uVar97 & uVar54) & uVar15
    ) & 0xFFFFFFFF
    uVar67 = ((~(uVar60 & 0xA258DB45) ^ uVar100) & uVar71 ^ (uVar100 ^ 0x5DA724BA) & uVar60 ^ uVar100 ^ 0xA258DB45) & 0xFFFFFFFF
    uVar97 = (
        (~((~uVar55 ^ uVar15) & uVar9) ^ uVar55 ^ uVar15) & uVar11 ^ ~((uVar97 ^ uVar9 ^ uVar54) & uVar15) & uVar55 ^ uVar97
    ) & 0xFFFFFFFF
    uVar7 = (
        ((uVar12 ^ uVar48) & (uVar79 ^ uVar37) ^ uVar78 ^ uVar37) & uVar70
        ^ (uVar79 ^ uVar36 ^ uVar12) & uVar37
        ^ (~uVar36 ^ uVar12) & uVar78
        ^ uVar12
    ) & 0xFFFFFFFF
    uVar54 = ((~(uVar101 & 0x5DA724BA) ^ uVar39 & 0x5DA724BA) & uVar22 ^ ~uVar101 & uVar39 ^ 0xA258DB45) & 0xFFFFFFFF
    uVar47 = (
        ((uVar87 & 0x5DA724BA ^ 0xA258DB45) & uVar75 ^ 0x5DA724BA) & uVar56 ^ (uVar75 ^ 0xA258DB45) & uVar87 ^ 0xA258DB45
    ) & 0xFFFFFFFF
    uVar39 = ((~uVar69 ^ uVar98 ^ uVar8) & src_dwords[6] ^ uVar98 ^ uVar3) & 0xFFFFFFFF
    uVar79 = (
        (~((~(uVar26 & uVar106) ^ uVar62 & (uVar93 ^ uVar96) ^ uVar96) & src_dwords[0x10]) ^ uVar26 & uVar80) & uVar103
        ^ ~(uVar26 & uVar46) & src_dwords[0x10]
    ) & 0xFFFFFFFF
    uVar106 = (
        ((~(src_dwords[0x14] & 0xFFDFDF77) ^ uVar25 & 0x5FDBDB27) & uVar26 ^ src_dwords[0x14] & 0xFFDFDF77) & 0xDFFFFFFF
    ) & 0xFFFFFFFF
    uVar33 = (~(uVar25 & 0x202088) & uVar26 & 0x5FFBFBAF ^ uVar33) & 0xFFFFFFFF
    uVar25 = (~uVar1) & 0xFFFFFFFF
    uVar69 = (~(uVar54 & uVar25) & src_dwords[0x1B] ^ uVar32) & 0xFFFFFFFF
    uVar72 = (
        (((uVar81 ^ uVar10) & uVar21 ^ uVar13 ^ uVar104) & src_dwords[0x1C] ^ uVar13 ^ uVar104) & uVar57
        ^ ((uVar81 & uVar21 ^ uVar13 ^ uVar104) & uVar10 ^ uVar13 ^ uVar104) & src_dwords[0x1C]
    ) & 0xFFFFFFFF
    uVar14 = (uVar14 & src_dwords[0x1C]) & 0xFFFFFFFF
    uVar88 = (
        ((uVar57 ^ uVar14) & uVar13 & uVar104 ^ (uVar72 ^ uVar104 ^ uVar74) & uVar53) & src_dwords[0x16]
        ^ (~uVar10 & uVar81 & uVar57 ^ uVar16) & src_dwords[0x1C]
    ) & 0xFFFFFFFF
    uVar9 = (~uVar27 ^ uVar33) & 0xFFFFFFFF
    uVar15 = (uVar9 & uVar106) & 0xFFFFFFFF
    uVar74 = (
        (uVar108 & uVar45 ^ uVar15 ^ uVar27 ^ uVar33) & uVar91 ^ (~uVar15 ^ uVar45 ^ uVar27 ^ uVar33) & uVar108 ^ uVar27
    ) & 0xFFFFFFFF
    uVar89 = ((~uVar27 ^ uVar106) & uVar33) & 0xFFFFFFFF
    uVar21 = (~uVar34) & 0xFFFFFFFF
    uVar101 = (
        (
            ((uVar75 & 0x5DA724BA ^ ~(uVar87 & 0x5DA724BA)) & uVar56 ^ (uVar87 ^ 0xA258DB45) & uVar75 ^ 0xA258DB45)
            & (uVar21 ^ uVar47)
            ^ uVar47
        )
        & src_dwords[0]
    ) & 0xFFFFFFFF
    uVar87 = (uVar89 ^ uVar27) & 0xFFFFFFFF
    uVar75 = (((uVar27 ^ uVar106) & (uVar64 ^ 0x1D9AEB51) ^ uVar64 ^ 0x1D9AEB51) & uVar33) & 0xFFFFFFFF
    uVar22 = (
        ((uVar27 ^ 0x9DAF5C9C) & uVar64 ^ uVar27 & 0x1D9AEB51 ^ uVar75 ^ 0xFFEF5CBE) & uVar30
        ^ ~((uVar87 ^ 0x9DAF5C9C) & uVar49) & uVar64
        ^ (uVar87 ^ 0x9DBFFFDD) & 0xE26514AE
    ) & 0xFFFFFFFF
    uVar16 = (~(uVar94 & ~uVar90) & src_dwords[10] ^ uVar90) & 0xFFFFFFFF
    uVar60 = (uVar60 ^ ~(uVar60 & uVar100 & 0xA258DB45) & uVar71) & 0xFFFFFFFF
    uVar17 = (uVar77 & 0xA258DB45) & 0xFFFFFFFF
    uVar24 = (((uVar17 ^ 0x5DA724BA) & uVar61 ^ uVar77) & uVar97 ^ ~(uVar61 & uVar77) & 0x5DA724BA) & 0xFFFFFFFF
    uVar55 = (
        (~uVar50 & uVar73 ^ uVar42 & uVar55 ^ uVar11) & uVar92 ^ (uVar42 & uVar55 ^ uVar11 ^ uVar50) & uVar73 ^ uVar55
    ) & 0xFFFFFFFF
    uVar11 = (src_dwords[0] & uVar21 & uVar47) & 0xFFFFFFFF
    uVar50 = (
        (~(uVar49 & 0xE26514AE) & uVar30 ^ uVar89 ^ uVar27 ^ 0x7FCA4832) & uVar64
        ^ (uVar87 & 0xE26514AE ^ 0x7FDAEB73) & uVar30
        ^ 0xE26514AE
    ) & 0xFFFFFFFF
    uVar21 = ((uVar61 ^ uVar17) & uVar97 ^ ~(uVar61 & uVar77) & 0xA258DB45) & 0xFFFFFFFF
    uVar71 = (~(uVar6 & src_dwords[0x15] & ~uVar67 & uVar60) ^ uVar6 ^ src_dwords[0x15]) & 0xFFFFFFFF
    uVar98 = ((uVar8 & ~src_dwords[6] ^ uVar98) & uVar3 ^ (uVar98 ^ src_dwords[6]) & uVar8 ^ uVar98) & 0xFFFFFFFF
    uVar3 = ((uVar64 ^ uVar49) & uVar30 ^ uVar49) & 0xFFFFFFFF
    uVar42 = (~(((~(uVar94 & ~uVar4) ^ uVar4) & src_dwords[10] ^ uVar94) & uVar90) ^ src_dwords[10]) & 0xFFFFFFFF
    uVar56 = (
        ((uVar3 ^ 0xC6D87455) & uVar35 ^ (uVar3 ^ 0x39278BAA) & uVar68 ^ uVar30 ^ 0xE26514AE) & uVar41
        ^ ((uVar68 ^ 0x1D9AEB51) & uVar49 ^ (uVar68 ^ 0xE26514AE) & uVar64 ^ 0xC6D87455) & uVar30
        ^ (uVar49 ^ 0xFB679FAE) & 0x1D9AEB51
        ^ (uVar49 ^ 0x39278BAA) & uVar68
    ) & 0xFFFFFFFF
    uVar12 = (
        ((uVar20 ^ uVar12 ^ uVar48) & uVar70 ^ uVar37 ^ uVar12) & uVar36 ^ (uVar37 ^ uVar12) & uVar70 ^ uVar78 ^ uVar12
    ) & 0xFFFFFFFF
    uVar3 = (~uVar45) & 0xFFFFFFFF
    uVar48 = ((~((uVar59 ^ uVar56) & uVar76) ^ uVar59 & uVar56) & src_dwords[0x19]) & 0xFFFFFFFF
    uVar73 = (
        ((uVar108 ^ uVar35 ^ uVar91) & uVar45 ^ (uVar3 ^ uVar35) & uVar41 ^ uVar35 ^ uVar91) & uVar68
        ^ (~(uVar41 & uVar35) ^ uVar108) & uVar45
        ^ uVar91
    ) & 0xFFFFFFFF
    uVar37 = (uVar59 ^ uVar48) & 0xFFFFFFFF
    uVar20 = (~uVar48 ^ uVar59) & 0xFFFFFFFF
    uVar48 = (uVar29 & uVar20) & 0xFFFFFFFF
    uVar36 = (~uVar59 ^ uVar29) & 0xFFFFFFFF
    uVar4 = (uVar59 & uVar29) & 0xFFFFFFFF
    uVar8 = (
        (~((uVar36 & uVar56 ^ uVar4) & uVar76) ^ ~(uVar29 & uVar56) & uVar59 ^ uVar29) & src_dwords[0x19]
        ^ (((uVar29 ^ uVar37) & uVar43 ^ uVar48) & uVar31 ^ uVar43 & uVar48) & src_dwords[0xB]
        ^ uVar59
        ^ uVar29
    ) & 0xFFFFFFFF
    uVar48 = (src_dwords[0x1B]) & 0xFFFFFFFF
    uVar70 = (~(((~(uVar32 & uVar25) ^ uVar1) & uVar54 ^ uVar32 ^ uVar1) & uVar48) ^ ~uVar32 & uVar1) & 0xFFFFFFFF
    uVar25 = ((~uVar48 & uVar1 ^ uVar48) & uVar32 ^ uVar48 & uVar25) & 0xFFFFFFFF
    uVar54 = (~uVar102) & 0xFFFFFFFF
    uVar14 = (
        ~(((~uVar14 ^ uVar57) & uVar13 & uVar104 ^ (uVar72 ^ uVar13 & uVar104) & uVar53) & src_dwords[0x16]) ^ uVar53 ^ uVar57
    ) & 0xFFFFFFFF
    uVar48 = (
        ((uVar18 ^ uVar102 ^ uVar88) & uVar14 ^ (uVar102 ^ uVar14) & uVar38 ^ uVar18 ^ uVar102) & uVar19
        ^ (~(uVar54 & uVar38) ^ uVar88) & uVar14
        ^ uVar88
    ) & 0xFFFFFFFF
    uVar94 = (
        ((uVar49 & 0xE26514AE ^ uVar27 ^ 0x9DAF5C9C) & uVar64 ^ uVar27 & 0x1D9AEB51 ^ uVar75 ^ 0xFFEF5CBE) & uVar30
        ^ ((uVar87 ^ 0x6250A363) & uVar49 ^ 0xE26514AE) & uVar64
        ^ (uVar87 ^ 0xFFEF5CBE) & 0x1D9AEB51
    ) & 0xFFFFFFFF
    uVar34 = (uVar34 ^ uVar47) & 0xFFFFFFFF
    uVar90 = (
        (~((~uVar18 ^ uVar102 ^ uVar88) & uVar14) ^ (uVar54 ^ uVar14) & uVar38 ^ uVar18 ^ uVar88) & uVar19
        ^ (~(uVar54 & uVar14) ^ uVar102) & uVar38
        ^ (uVar18 ^ uVar88) & uVar14
        ^ uVar18
    ) & 0xFFFFFFFF
    uVar1 = (uVar105 ^ uVar28) & 0xFFFFFFFF
    uVar87 = (
        (~(uVar9 & uVar91) ^ uVar108 & uVar9 ^ uVar27 ^ uVar33) & uVar106
        ^ (~(~uVar108 & uVar45) ^ uVar33) & uVar91
        ^ (uVar45 ^ uVar33) & uVar108
        ^ uVar45
        ^ uVar27
        ^ uVar33
    ) & 0xFFFFFFFF
    uVar64 = ((~(uVar1 & uVar18) ^ uVar105 ^ uVar28) & uVar14 ^ uVar1 & (uVar18 ^ uVar14) & uVar88 ^ uVar28) & 0xFFFFFFFF
    uVar78 = (~(~uVar99 & uVar7) & 0x5DA724BA ^ (uVar99 & 0x5DA724BA ^ 0xA258DB45) & uVar12) & 0xFFFFFFFF
    uVar83 = (
        ~(
            (
                ~(
                    (~((~(uVar26 & uVar83) ^ uVar2 ^ uVar96) & uVar103) ^ (~uVar23 ^ uVar2 ^ uVar96) & uVar26 ^ uVar2 ^ uVar96)
                    & uVar62
                )
                ^ (~(uVar26 & uVar107) ^ uVar103) & uVar96
                ^ uVar103
            )
            & src_dwords[0x10]
        )
        ^ uVar26 & uVar103 & uVar80
    ) & 0xFFFFFFFF
    uVar26 = (~uVar84) & 0xFFFFFFFF
    uVar72 = (
        ~(((uVar59 ^ uVar83 ^ uVar56 ^ uVar79) & uVar84 ^ uVar83) & uVar76) ^ uVar26 & uVar83 ^ uVar84 ^ uVar59
    ) & 0xFFFFFFFF
    uVar75 = (
        (~uVar106 & uVar33 ^ uVar45 & ~uVar91) & uVar27
        ^ ~(((uVar3 ^ uVar27) & uVar91 ^ uVar15 ^ uVar45 ^ uVar27 ^ uVar33) & uVar108)
        ^ uVar91
    ) & 0xFFFFFFFF
    uVar33 = (~uVar59 & uVar83) & 0xFFFFFFFF
    uVar89 = (
        ((uVar76 ^ uVar83 ^ uVar79) & uVar59 ^ uVar83) & uVar84 ^ ~((uVar26 ^ uVar59) & uVar56) & uVar76 ^ uVar59 ^ uVar33
    ) & 0xFFFFFFFF
    uVar49 = ((~uVar77 & uVar61 & 0xA258DB45 ^ 0x5DA724BA) & uVar97 ^ ~uVar17 & uVar61) & 0xFFFFFFFF
    uVar27 = (~((~(uVar12 & 0xA258DB45) & uVar99 ^ 0xA258DB45) & uVar7) ^ uVar12) & 0xFFFFFFFF
    uVar7 = (~((~(uVar7 & 0xA258DB45) & uVar99 ^ 0x5DA724BA) & uVar12) ^ uVar99 & 0x5DA724BA ^ uVar7) & 0xFFFFFFFF
    uVar47 = ((uVar94 ^ uVar50) & uVar22) & 0xFFFFFFFF
    uVar32 = (~uVar47 ^ uVar94) & 0xFFFFFFFF
    uVar92 = (src_dwords[7] & uVar32) & 0xFFFFFFFF
    uVar47 = (~(uVar105 & uVar92) ^ uVar94 ^ uVar47) & 0xFFFFFFFF
    uVar12 = (
        (
            ((uVar1 & uVar22 ^ uVar105 ^ uVar28) & uVar94 ^ uVar1 & uVar50 & uVar22 ^ uVar105 ^ uVar28) & uVar82 & src_dwords[7]
            ^ uVar47 & uVar28
        )
        & src_dwords[1]
        ^ uVar28
        ^ src_dwords[7]
    ) & 0xFFFFFFFF
    uVar1 = (
        ~(((uVar66 ^ src_dwords[4]) & uVar58 ^ uVar66 ^ src_dwords[4]) & uVar44 & src_dwords[0xD]) ^ uVar66 ^ src_dwords[4]
    ) & 0xFFFFFFFF
    uVar106 = (src_dwords[0xC]) & 0xFFFFFFFF
    uVar77 = ((~(~uVar49 & uVar106) & uVar24 ^ uVar106) & uVar21 ^ uVar24) & 0xFFFFFFFF
    uVar15 = ((uVar24 & ~uVar106 ^ uVar106) & uVar21 ^ uVar106) & 0xFFFFFFFF
    uVar17 = (
        ((uVar80 ^ uVar95) & (uVar84 ^ uVar83) ^ uVar80 ^ uVar95) & uVar103
        ^ (uVar84 ^ uVar95 ^ uVar79) & uVar83
        ^ ~(uVar95 & (uVar26 ^ uVar83)) & uVar80
        ^ (uVar95 ^ uVar79) & uVar84
        ^ uVar95
    ) & 0xFFFFFFFF
    uVar91 = (
        ~(((uVar45 ^ uVar35) & uVar68 ^ uVar3 & uVar35) & uVar41) ^ ~((~uVar108 ^ uVar35 ^ uVar91) & uVar68) & uVar45 ^ uVar91
    ) & 0xFFFFFFFF
    uVar33 = (
        (~(uVar84 & (~uVar83 ^ uVar79)) ^ uVar59 & uVar56 ^ uVar83) & uVar76
        ^ (uVar59 & (~uVar83 ^ uVar79) ^ uVar83 ^ uVar79) & uVar84
        ^ uVar33
    ) & 0xFFFFFFFF
    uVar3 = ((uVar75 ^ uVar74) & uVar87 ^ uVar75 ^ 0xECB2D69E) & 0xFFFFFFFF
    uVar37 = (uVar29 & uVar37) & 0xFFFFFFFF
    uVar20 = (~((((uVar29 ^ uVar20) & uVar43 ^ uVar37) & uVar31 ^ uVar43 & uVar37) & src_dwords[0xB]) ^ uVar59) & 0xFFFFFFFF
    uVar30 = (uVar20 ^ uVar29) & 0xFFFFFFFF
    uVar32 = (uVar32 & src_dwords[1]) & 0xFFFFFFFF
    uVar9 = (
        ~(((uVar105 ^ uVar32) & uVar28 ^ ~uVar32 & uVar105) & uVar82 & src_dwords[7])
        ^ (~(uVar47 & src_dwords[1]) ^ src_dwords[7]) & uVar28
        ^ uVar32
    ) & 0xFFFFFFFF
    uVar47 = (((uVar27 ^ ~uVar7) & uVar78 ^ uVar7 ^ uVar27) & src_dwords[0xF] ^ uVar27 & ~uVar7) & 0xFFFFFFFF
    uVar61 = (
        ((uVar18 ^ uVar14) & uVar88 ^ uVar18 & uVar14 ^ uVar82) & (uVar28 ^ ~uVar105) ^ uVar105 & ~uVar28 ^ uVar14
    ) & 0xFFFFFFFF
    uVar23 = (
        ~((~((uVar102 ^ uVar38) & uVar14) ^ (uVar102 ^ uVar38) & uVar88) & uVar19)
        ^ ((uVar14 ^ uVar88) & uVar102 ^ uVar14 ^ uVar88) & uVar38
        ^ ~(~uVar14 & uVar18) & uVar88
    ) & 0xFFFFFFFF
    uVar35 = (
        ((uVar74 ^ 0xECB2D69E) & uVar75 ^ uVar74 & 0xECB2D69E ^ 0x134D2961) & uVar87 ^ ~(uVar74 & 0x134D2961) & uVar75
    ) & 0xFFFFFFFF
    uVar21 = (~((~(~uVar24 & uVar21) ^ uVar24) & uVar49 & uVar106) ^ (uVar21 ^ ~uVar106) & uVar24 ^ uVar21) & 0xFFFFFFFF
    uVar37 = (~(((uVar91 ^ 0x134D2961) & uVar51 ^ ~uVar91 & 0xECB2D69E) & uVar73) ^ uVar91 & 0xECB2D69E) & 0xFFFFFFFF
    uVar88 = (
        (~uVar28 & uVar14 ^ uVar18 & (uVar28 ^ uVar14)) & uVar88
        ^ ((~uVar18 ^ uVar82) & uVar28 ^ uVar18 ^ uVar82) & uVar14
        ^ ~(uVar82 & (uVar28 ^ uVar14)) & uVar105
    ) & 0xFFFFFFFF
    uVar14 = ((uVar73 & 0x134D2961 ^ 0xECB2D69E) & uVar51 ^ ~uVar73 & uVar91 & 0x134D2961 ^ uVar73 ^ 0xECB2D69E) & 0xFFFFFFFF
    uVar87 = ((uVar75 & uVar74 ^ 0xECB2D69E) & uVar87 ^ uVar75 ^ uVar74 & 0x134D2961 ^ 0xECB2D69E) & 0xFFFFFFFF
    uVar97 = (
        ((~uVar67 ^ uVar60) & src_dwords[0x15] ^ uVar67 ^ uVar60) & uVar6 ^ (uVar67 ^ uVar60) & src_dwords[0x15]
    ) & 0xFFFFFFFF
    uVar41 = (
        ~(((~uVar61 ^ uVar25 ^ uVar70) & uVar88 ^ uVar61 ^ uVar25 ^ uVar70) & uVar69)
        ^ (uVar88 ^ uVar69) & uVar61 & uVar64
        ^ uVar25
    ) & 0xFFFFFFFF
    uVar49 = (src_dwords[0x12]) & 0xFFFFFFFF
    uVar68 = ((~((~uVar3 & uVar35 ^ uVar3) & uVar49) ^ uVar35) & uVar87 ^ uVar35 & uVar49) & 0xFFFFFFFF
    uVar5 = (
        ~(
            (
                ((src_dwords[4] ^ src_dwords[0xD]) & uVar66 ^ ~src_dwords[4] & src_dwords[0xD] ^ src_dwords[4]) & uVar58
                ^ (uVar5 ^ uVar66) & src_dwords[4]
            )
            & uVar44
        )
        ^ (uVar5 ^ src_dwords[4]) & uVar66
        ^ src_dwords[0xD]
    ) & 0xFFFFFFFF
    uVar106 = (
        (~((~uVar38 ^ uVar5) & uVar1) ^ uVar38 ^ uVar5) & uVar40
        ^ ((uVar54 ^ uVar19 ^ uVar1) & uVar38 ^ uVar102) & uVar5
        ^ uVar54 & uVar38
        ^ uVar102
        ^ uVar1
    ) & 0xFFFFFFFF
    uVar24 = (
        ~(((uVar102 ^ uVar19) & uVar38 ^ (uVar40 ^ uVar38) & uVar1 ^ uVar40 ^ uVar102) & uVar5)
        ^ (~(~uVar40 & uVar1) ^ uVar40 ^ uVar19) & uVar38
        ^ uVar1
    ) & 0xFFFFFFFF
    uVar44 = ((~(uVar3 & uVar49) ^ uVar87) & uVar35 ^ (uVar87 ^ uVar3) & uVar49 ^ uVar87) & 0xFFFFFFFF
    uVar74 = (~uVar29) & 0xFFFFFFFF
    uVar60 = (
        ~((~((~(~uVar6 & uVar60) ^ uVar6) & src_dwords[0x15]) ^ uVar6) & uVar67) ^ (src_dwords[0x15] ^ uVar60) & uVar6 ^ uVar60
    ) & 0xFFFFFFFF
    uVar54 = (
        (((uVar59 ^ uVar29) & uVar56 ^ uVar59 & uVar74) & uVar76 ^ ~(uVar74 & uVar56) & uVar59 ^ uVar29) & src_dwords[0x19]
        ^ ((uVar36 & uVar43 ^ uVar4) & uVar31 ^ uVar4 & uVar43) & src_dwords[0xB]
    ) & 0xFFFFFFFF
    uVar45 = ((~(~uVar27 & uVar7) ^ uVar27) & uVar78 & src_dwords[0xF] ^ uVar7 ^ uVar27) & 0xFFFFFFFF
    uVar6 = (
        ~((~((uVar40 ^ uVar102 ^ uVar19 ^ uVar5) & uVar38) ^ uVar102) & uVar1) ^ (uVar40 ^ uVar19 ^ uVar5) & uVar38 ^ uVar5
    ) & 0xFFFFFFFF
    uVar4 = ((uVar54 ^ uVar30) & (uVar31 ^ uVar29)) & 0xFFFFFFFF
    uVar56 = ((~(uVar54 & (uVar31 ^ uVar29)) ^ uVar31 ^ uVar29) & uVar30 ^ uVar4 & uVar8 ^ uVar29) & 0xFFFFFFFF
    uVar58 = (
        ~((~((uVar84 ^ uVar79) & uVar83) ^ (uVar26 ^ uVar95) & uVar79 ^ uVar103 & (uVar46 ^ uVar79)) & uVar80)
        ^ (~uVar103 & uVar95 ^ uVar26 & uVar83 ^ uVar84) & uVar79
        ^ uVar84
        ^ uVar83
    ) & 0xFFFFFFFF
    uVar59 = (~uVar88 ^ uVar64) & 0xFFFFFFFF
    uVar66 = (uVar59 & uVar61) & 0xFFFFFFFF
    uVar49 = (~uVar23 ^ uVar90) & 0xFFFFFFFF
    uVar18 = (
        ~(((uVar49 ^ uVar71) & uVar48 ^ uVar71) & uVar60) ^ ~((uVar60 ^ uVar48) & uVar97) & uVar71 ^ uVar49 & uVar48 ^ uVar90
    ) & 0xFFFFFFFF
    uVar49 = (~uVar5) & 0xFFFFFFFF
    uVar19 = (
        ~((~(uVar81 & (uVar49 ^ uVar1)) ^ uVar49 & uVar1 ^ uVar5) & uVar40)
        ^ ((uVar5 ^ uVar10) & uVar81 ^ uVar49 & uVar10) & uVar57
        ^ uVar5
        ^ uVar10
    ) & 0xFFFFFFFF
    uVar7 = (~((~(~uVar78 & src_dwords[0xF]) & uVar27 ^ src_dwords[0xF]) & uVar7) ^ src_dwords[0xF]) & 0xFFFFFFFF
    uVar27 = ((uVar73 ^ 0xECB2D69E) & uVar51 & uVar91 ^ (uVar91 ^ 0xECB2D69E) & uVar73 ^ 0xECB2D69E) & 0xFFFFFFFF
    uVar51 = (
        ~((uVar54 ^ uVar4 ^ uVar30) & uVar8)
        ^ ~(uVar54 & (~uVar31 ^ uVar29)) & uVar30
        ^ uVar31 & uVar74
        ^ (~uVar31 ^ uVar29) & uVar43
    ) & 0xFFFFFFFF
    uVar4 = (uVar40 & (uVar49 ^ uVar1)) & 0xFFFFFFFF
    uVar1 = (
        ((uVar49 ^ uVar10) & uVar57 ^ uVar4 ^ uVar5 ^ uVar10) & uVar81 ^ (uVar40 & uVar1 ^ uVar52) & uVar5 ^ uVar10
    ) & 0xFFFFFFFF
    uVar49 = (uVar106 ^ ~uVar6) & 0xFFFFFFFF
    uVar36 = (
        (uVar49 & uVar15 ^ uVar6 ^ uVar106) & uVar77 ^ ((uVar15 ^ uVar77) & uVar21 ^ uVar24) & uVar49 ^ uVar106
    ) & 0xFFFFFFFF
    uVar5 = ((~uVar4 ^ uVar57) & uVar81 ^ (uVar4 ^ uVar57) & uVar10 ^ uVar5) & 0xFFFFFFFF
    uVar10 = (~(((~(uVar82 & ~uVar105) ^ uVar105) & src_dwords[7] ^ uVar32) & uVar28) ^ uVar92 & src_dwords[1]) & 0xFFFFFFFF
    uVar32 = ((~uVar35 & uVar3 & src_dwords[0x12] ^ uVar35) & uVar87 ^ src_dwords[0x12]) & 0xFFFFFFFF
    uVar87 = (~uVar54) & 0xFFFFFFFF
    uVar20 = (
        ((uVar87 ^ uVar29) & uVar30 ^ uVar54 & uVar29) & uVar8
        ^ ((uVar87 ^ uVar43) & uVar29 ^ uVar54 ^ uVar43) & uVar30
        ^ ~(uVar20 & uVar43) & uVar31
    ) & 0xFFFFFFFF
    uVar4 = (~uVar10) & 0xFFFFFFFF
    uVar3 = ((uVar13 ^ uVar10 ^ uVar104 ^ uVar9) & uVar12) & 0xFFFFFFFF
    uVar52 = (
        ~((uVar4 & uVar9 ^ uVar10 ^ uVar3) & uVar53) ^ (uVar10 & uVar9 ^ uVar13 ^ uVar104) & uVar12 ^ uVar10 ^ uVar104
    ) & 0xFFFFFFFF
    uVar49 = ((uVar4 ^ uVar104) & uVar13) & 0xFFFFFFFF
    uVar91 = (uVar10 & ~uVar104) & 0xFFFFFFFF
    uVar28 = (~uVar89 ^ uVar72) & 0xFFFFFFFF
    uVar67 = (
        ~(((uVar104 ^ uVar9) & uVar10 ^ uVar49 ^ uVar3 ^ uVar104 ^ uVar9) & uVar53)
        ^ ((uVar10 ^ uVar9) & uVar104 ^ uVar13 ^ uVar10 ^ uVar9) & uVar12
        ^ (~uVar91 ^ uVar104) & uVar9
        ^ uVar10
        ^ uVar49
        ^ uVar104
    ) & 0xFFFFFFFF
    uVar57 = (
        ~((~(uVar44 & uVar28) ^ uVar28 & uVar68 ^ uVar89 ^ uVar72) & uVar32)
        ^ (~uVar68 ^ uVar33 ^ uVar89) & uVar72
        ^ (uVar28 & uVar68 ^ uVar89 ^ uVar72) & uVar44
        ^ (uVar68 ^ uVar33) & uVar89
        ^ uVar68
        ^ uVar33
    ) & 0xFFFFFFFF
    uVar95 = (
        (
            (uVar95 ^ uVar79 ^ uVar26 ^ uVar83) & uVar103
            ^ (uVar26 ^ uVar95 ^ uVar79) & uVar83
            ^ uVar84 & (uVar46 ^ uVar79)
            ^ uVar46 & uVar79
        )
        & uVar80
        ^ ((uVar79 ^ uVar84 ^ uVar83) & uVar103 ^ uVar84 ^ uVar83 ^ uVar79) & uVar95
        ^ ~(uVar84 & uVar83) & uVar79
    ) & 0xFFFFFFFF
    uVar49 = (src_dwords[3]) & 0xFFFFFFFF
    uVar29 = ((~uVar49 & uVar14 ^ uVar49) & uVar27 ^ uVar14) & 0xFFFFFFFF
    uVar31 = (~((~((~uVar37 & uVar14 ^ uVar37) & uVar27) ^ uVar14) & uVar49) ^ uVar27) & 0xFFFFFFFF
    uVar26 = (~uVar50) & 0xFFFFFFFF
    uVar87 = (uVar87 ^ uVar8) & 0xFFFFFFFF
    uVar35 = (
        ~(((uVar54 ^ uVar8) & (uVar26 ^ uVar22) ^ uVar50 ^ uVar22) & uVar94)
        ^ (~(uVar87 & uVar50) ^ uVar54 ^ uVar8) & uVar22
        ^ (uVar30 ^ uVar50) & uVar87
        ^ uVar54
    ) & 0xFFFFFFFF
    uVar3 = ((~uVar65 ^ uVar55) & uVar63 & 0xECB2D69E ^ uVar55) & 0xFFFFFFFF
    uVar38 = (~uVar62 ^ uVar10) & 0xFFFFFFFF
    uVar46 = (
        ((uVar4 ^ uVar9) & uVar12 ^ uVar62 & uVar10 ^ uVar38 & uVar96 ^ uVar9) & uVar2
        ^ (~uVar96 & uVar62 ^ ~uVar12 & uVar9) & uVar10
        ^ uVar62
        ^ uVar12
    ) & 0xFFFFFFFF
    uVar4 = ((uVar2 ^ uVar62) & uVar96) & 0xFFFFFFFF
    uVar80 = ((~(~uVar55 & uVar65 & 0x134D2961) ^ uVar55) & uVar63 ^ (uVar55 ^ 0x134D2961) & uVar65 ^ 0x134D2961) & 0xFFFFFFFF
    uVar40 = (
        (~((uVar2 ^ uVar10 ^ uVar9) & uVar62) ^ uVar2 ^ uVar4) & uVar12
        ^ (~(uVar93 & uVar96) ^ uVar10 ^ uVar9) & uVar62
        ^ uVar2
        ^ uVar10
    ) & 0xFFFFFFFF
    uVar63 = (((uVar65 & 0x134D2961 ^ 0xECB2D69E) & uVar63 ^ ~uVar65 & 0xECB2D69E) & uVar55 ^ uVar65 & 0xECB2D69E) & 0xFFFFFFFF
    uVar14 = ((~(uVar49 & uVar37) & uVar27 ^ uVar49) & uVar14 ^ uVar27 & ~uVar49) & 0xFFFFFFFF
    uVar27 = ((~((~uVar3 ^ uVar63) & uVar80) ^ uVar3 ^ uVar63) & src_dwords[0x18] ^ uVar3 ^ uVar80) & 0xFFFFFFFF
    uVar49 = (~((uVar50 ^ uVar22) & uVar94) ^ uVar26 & uVar22) & 0xFFFFFFFF
    uVar37 = ((uVar49 ^ uVar54 ^ uVar50) & uVar8 ^ (uVar49 ^ uVar50) & uVar54 ^ uVar94) & 0xFFFFFFFF
    uVar49 = ((src_dwords[0x18] ^ uVar63) & uVar80) & 0xFFFFFFFF
    uVar43 = (~((~src_dwords[0x18] & uVar63 ^ src_dwords[0x18]) & uVar3) ^ uVar49) & 0xFFFFFFFF
    uVar53 = (
        ((uVar53 ^ uVar9) & uVar10 ^ uVar53 ^ uVar9) & uVar104
        ^ (~((uVar10 ^ uVar104) & uVar9) ^ uVar91) & uVar12
        ^ (uVar53 & (uVar10 ^ uVar104) ^ uVar10 ^ uVar104) & uVar13
        ^ uVar53
    ) & 0xFFFFFFFF
    uVar8 = (
        ((uVar54 ^ uVar50) & uVar22 ^ uVar87 & uVar30 ^ uVar54 & uVar26) & uVar94
        ^ (uVar30 & uVar8 ^ uVar26 & uVar22 ^ uVar50) & uVar54
        ^ uVar8
    ) & 0xFFFFFFFF
    uVar63 = (((uVar63 ^ uVar80) & src_dwords[0x18] ^ uVar63) & uVar3 ^ uVar49 ^ src_dwords[0x18] ^ uVar63) & 0xFFFFFFFF
    uVar49 = (~((~uVar7 ^ uVar45) & uVar17)) & 0xFFFFFFFF
    uVar13 = (
        ~(((~uVar7 ^ uVar45) & uVar95 ^ uVar49 ^ uVar7 ^ uVar45) & uVar58)
        ^ (~(~uVar47 & uVar7) ^ uVar47 ^ uVar17) & uVar45
        ^ (uVar49 ^ uVar7 ^ uVar45) & uVar95
        ^ (uVar47 ^ uVar17) & uVar7
        ^ uVar47
    ) & 0xFFFFFFFF
    uVar22 = (
        (~((uVar31 ^ uVar19) & uVar1) ^ uVar31 ^ uVar19) & uVar5
        ^ (~((uVar29 ^ uVar1 ^ uVar14) & uVar19) ^ uVar14) & uVar31
        ^ (uVar29 ^ uVar1) & uVar19
    ) & 0xFFFFFFFF
    uVar2 = (
        ~(((uVar38 ^ uVar9 ^ uVar96) & uVar2 ^ (uVar10 ^ uVar96) & uVar62 ^ uVar38 & uVar9) & uVar12)
        ^ (uVar62 & uVar93 ^ ~uVar4) & uVar10
        ^ (uVar62 ^ uVar10 ^ uVar93) & uVar9
        ^ uVar2
    ) & 0xFFFFFFFF
    uVar62 = ((~uVar63 ^ uVar43) & uVar27) & 0xFFFFFFFF
    uVar3 = (~uVar51 & uVar56 ^ uVar62 ^ uVar51) & 0xFFFFFFFF
    uVar9 = (
        (~((~uVar63 ^ uVar43) & uVar51) ^ uVar63 ^ uVar43) & uVar27
        ^ (~uVar56 ^ uVar63 ^ uVar43) & uVar51
        ^ (uVar3 ^ uVar63 ^ uVar43) & uVar20
        ^ uVar56
        ^ uVar43
    ) & 0xFFFFFFFF
    uVar55 = ((~uVar86 ^ uVar42) & uVar16) & 0xFFFFFFFF
    uVar4 = (((uVar35 ^ uVar16) & uVar37 ^ uVar55 ^ uVar42) & uVar8 ^ (~uVar35 & uVar37 ^ uVar86) & uVar16 ^ uVar35) & 0xFFFFFFFF
    uVar49 = ((uVar34 ^ uVar11) & uVar2) & 0xFFFFFFFF
    uVar30 = (~uVar34 & uVar101) & 0xFFFFFFFF
    uVar38 = (
        ~(((uVar34 ^ uVar11) & uVar40 ^ ~uVar49 ^ uVar34 ^ uVar11) & uVar46)
        ^ (uVar49 ^ uVar34 ^ uVar11) & uVar40
        ^ ~uVar30 & uVar11
        ^ uVar34
        ^ uVar2
    ) & 0xFFFFFFFF
    uVar49 = ((~uVar11 ^ uVar101) & uVar34) & 0xFFFFFFFF
    uVar55 = (~((~uVar55 ^ uVar42) & uVar8) ^ (uVar55 ^ uVar42) & uVar35 ^ uVar16) & 0xFFFFFFFF
    uVar12 = (~uVar67) & 0xFFFFFFFF
    uVar10 = (
        (uVar39 & (uVar67 ^ uVar52) ^ uVar67 ^ uVar52) & uVar98 ^ ~(uVar85 & (uVar67 ^ uVar52)) & uVar39 ^ uVar52
    ) & 0xFFFFFFFF
    uVar26 = ((uVar52 ^ uVar12) & uVar53) & 0xFFFFFFFF
    uVar49 = (
        ~(~((~uVar49 ^ uVar46 ^ uVar11 ^ uVar101) & uVar2) ^ (uVar49 ^ uVar11 ^ uVar101) & uVar46 ^ uVar34 ^ uVar11)
    ) & 0xFFFFFFFF
    uVar12 = (
        ((uVar85 ^ uVar52 ^ uVar98) & uVar67 ^ uVar98 ^ uVar26) & uVar39
        ^ (~(uVar52 & uVar12) ^ uVar67) & uVar53
        ^ uVar98 & uVar12
        ^ uVar67
        ^ uVar52
    ) & 0xFFFFFFFF
    dst_dwords[0] = (
        ~(
            (
                ~((~((uVar95 ^ uVar7 ^ uVar47) & uVar17) ^ (~uVar95 ^ uVar17) & uVar58 ^ uVar95) & uVar45)
                ^ (uVar95 & uVar58 ^ uVar7 ^ uVar47) & uVar17
                ^ uVar7
                ^ uVar13
            )
            & (
                ((uVar95 ^ uVar17) & (uVar7 ^ uVar45) ^ uVar7 ^ uVar45) & uVar58
                ^ (uVar17 & (uVar7 ^ uVar45) ^ uVar7 ^ uVar45) & uVar95
                ^ (~uVar47 & uVar45 ^ uVar47) & uVar7
                ^ uVar17
            )
        )
        ^ (
            (~((uVar46 ^ uVar34 ^ uVar40) & uVar11) ^ (uVar46 ^ uVar101 ^ uVar40) & uVar34 ^ uVar101 ^ uVar40) & uVar2
            ^ (~((~uVar101 ^ uVar40) & uVar34) ^ (~uVar34 ^ uVar40) & uVar11 ^ uVar101 ^ uVar40) & uVar46
            ^ (uVar30 ^ uVar34 ^ uVar40) & uVar11
            ^ (uVar101 ^ uVar40) & uVar34
            ^ uVar101
            ^ uVar40
        )
        & (uVar38 ^ uVar49)
        ^ uVar38 & uVar49
        ^ uVar13
    ) & 0xFFFFFFFF
    uVar47 = (
        ~(
            ((~uVar31 ^ uVar19) & uVar1 ^ (~uVar29 ^ uVar14) & uVar31 ^ uVar29) & uVar5
            ^ (uVar1 & uVar19 ^ uVar14) & uVar31
            ^ uVar19
        )
    ) & 0xFFFFFFFF
    uVar49 = (
        ~(
            ~((~((~uVar60 ^ uVar23) & uVar48) ^ (uVar60 ^ uVar48) & uVar71 ^ uVar60) & uVar90)
            ^ ((uVar60 ^ uVar23) & uVar71 ^ uVar60 & ~uVar23) & uVar48
            ^ ~((uVar60 ^ uVar90 ^ uVar48) & uVar97) & uVar71
        )
    ) & 0xFFFFFFFF
    dst_dwords[1] = (
        ~(
            (
                (~((uVar68 ^ uVar89) & uVar32) ^ (uVar68 ^ uVar72) & uVar89 ^ uVar28 & uVar33 ^ uVar72) & uVar44
                ^ (uVar33 & uVar72 ^ uVar32 & ~uVar68 ^ uVar68) & uVar89
                ^ uVar57
                ^ uVar72
            )
            & (
                ((uVar44 ^ uVar68) & (uVar89 ^ uVar72) ^ uVar89 ^ uVar72) & uVar32
                ^ (uVar44 & (uVar89 ^ uVar72) ^ uVar89 ^ uVar72) & uVar68
                ^ ~uVar89 & uVar72
                ^ uVar44
                ^ uVar89
            )
        )
        ^ (~(((uVar5 ^ uVar19) & (~uVar29 ^ uVar14) ^ uVar29 ^ uVar14) & uVar31) ^ (~uVar5 ^ uVar19) & uVar29 ^ uVar5)
        & (uVar47 ^ uVar22)
        ^ uVar47 & uVar22
        ^ uVar57
    ) & 0xFFFFFFFF
    dst_dwords[2] = (
        ~(
            (
                ~(((~uVar85 ^ uVar67 ^ uVar98) & uVar52 ^ uVar85 ^ uVar67 ^ uVar26) & uVar39)
                ^ (uVar67 & uVar53 ^ uVar98) & uVar52
                ^ uVar67
            )
            & (uVar12 ^ uVar10)
        )
        ^ (
            (~((uVar60 ^ uVar97 ^ uVar48) & uVar90) ^ uVar60 ^ uVar97 ^ uVar48) & uVar71
            ^ ~((uVar90 ^ uVar71) & uVar23) & uVar48
            ^ uVar60
            ^ uVar90
        )
        & (uVar18 ^ uVar49)
        ^ uVar12 & uVar10
        ^ uVar18 & uVar49
    ) & 0xFFFFFFFF
    uVar48 = (~((~(uVar59 & uVar69) ^ uVar88 ^ uVar64) & uVar61 ^ ~((~uVar66 ^ uVar70 & uVar69) & uVar25) ^ uVar88)) & 0xFFFFFFFF
    dst_dwords[3] = (
        (
            ((uVar20 ^ uVar56 ^ uVar27) & uVar51 ^ uVar20 ^ uVar56) & uVar63
            ^ ((uVar51 ^ uVar63) & uVar27 ^ uVar51 ^ uVar63) & uVar43
            ^ ~uVar27 & uVar51
            ^ uVar20
            ^ uVar9
        )
        & ((uVar3 ^ uVar43) & uVar20 ^ (uVar62 ^ uVar43) & uVar51 ^ uVar63)
        ^ (
            ~((~((uVar86 ^ uVar42 ^ uVar37) & uVar35) ^ uVar42 ^ uVar37) & uVar16)
            ^ ((~uVar35 ^ uVar16) & uVar37 ^ uVar35 ^ uVar16) & uVar8
            ^ (uVar42 ^ uVar37) & uVar35
            ^ uVar42
            ^ uVar37
        )
        & (uVar55 ^ uVar4)
        ^ ~uVar55 & uVar4
        ^ uVar55
        ^ uVar9
    ) & 0xFFFFFFFF
    dst_dwords[4] = (
        (
            ~((uVar15 & (uVar6 ^ uVar77) ^ ~uVar6 & uVar77) & uVar21)
            ^ (~((uVar24 ^ uVar15) & uVar6) ^ uVar24 ^ uVar15) & uVar77
            ^ (~(uVar24 & (uVar6 ^ uVar77)) ^ uVar6 ^ uVar77) & uVar106
            ^ uVar36
        )
        & (~(uVar15 & (uVar6 ^ uVar106)) & uVar77 ^ (uVar15 ^ uVar77) & uVar21 & (uVar6 ^ uVar106) ^ ~uVar106 & uVar6 ^ uVar106)
        ^ ((~((~uVar88 ^ uVar70) & uVar69) ^ uVar66 ^ uVar88) & uVar25 ^ (uVar61 & uVar64 ^ ~(uVar70 & uVar69)) & uVar88 ^ uVar69)
        & (uVar41 ^ uVar48)
        ^ uVar41 & uVar48
        ^ uVar36
    ) & 0xFFFFFFFF

    destination[: len(dst_dwords) * 4] = _from_uints(dst_dwords)
