"""Public-key store for the S7CommPlus session-key handshake.

The PLC tells the client which public key to use via the
``ObjectVariableTypeName`` attribute (id 233) in its CreateObject
response — a UTF-8 WString shaped ``"FF:HHHHHHHHHHHHHHHH"`` where ``FF``
is the two-hex-digit family number and ``HHHH...`` is the 16-hex-digit
key fingerprint. Only families 0 (S7-1500), 1 (S7-1200) and 3 (PlcSim)
are supported, matching upstream HarpoS7 1.1.0.

Key bytes are vendored from ``bonk-dev/HarpoS7`` MIT-licensed binaries
in ``HarpoS7.PublicKeys/Keys/{FF}/{HHHH...}.bin``. The values were
extracted verbatim from each ``.bin`` file as hex.
"""

from __future__ import annotations

from enum import IntEnum

PUBLIC_KEY_LENGTH_REAL_PLC = 40
PUBLIC_KEY_LENGTH_PLCSIM = 64


class KeyFamily(IntEnum):
    """Public-key family advertised by the PLC.

    The two-hex-digit prefix of the ``ObjectVariableTypeName`` WString
    decodes to one of these values.
    """

    S7_1500 = 0x00
    S7_1200 = 0x01
    PLCSIM = 0x03


class UnknownPublicKeyError(LookupError):
    """Raised when the fingerprint advertised by the PLC has no
    matching public key in the bundled store."""

    def __init__(self, fingerprint: str) -> None:
        super().__init__(f"No public key for fingerprint {fingerprint!r}")
        self.fingerprint = fingerprint


# Public keys, keyed by (family, key_id). Vendored verbatim from
# bonk-dev/HarpoS7/HarpoS7.PublicKeys/Keys/{family}/{key_id}.bin.
_PUBLIC_KEYS: dict[tuple[KeyFamily, str], bytes] = {
    # Family 0 — S7-1500 (40-byte keys)
    (KeyFamily.S7_1500, "0448ACCBD5A0BFD2"): bytes.fromhex(
        "9808369442d4f3b63f9aa40856ddf798579966bc2a9c382c3fbf13a4d00aaa98ffefc9ab38da5537"
    ),
    (KeyFamily.S7_1500, "181B7B0847D11694"): bytes.fromhex(
        "8456a26996122216c921c571ff11e0befafdb1d70b5d4bc8390f5b0cc273ec142a03f2a04e6f1593"
    ),
    (KeyFamily.S7_1500, "1B580465BB0551B2"): bytes.fromhex(
        "d1c451071e18c526a423a9cd21349f01b6ccd9f2dda9e4dc2ff11356c9116b6dba611dc02995c097"
    ),
    (KeyFamily.S7_1500, "2C1DD211E529278D"): bytes.fromhex(
        "7de32536eac89a3558b82ee98f963bda6e7c179fddb3eeed2e30e446686eced971bb5478d112a3da"
    ),
    (KeyFamily.S7_1500, "580B8A122D42D1C0"): bytes.fromhex(
        "6ca1bbad4697ed515424db6b897e9d0c33e2ead0bce5566f257c1bd1dc714bad41f14ed9536cfda2"
    ),
    (KeyFamily.S7_1500, "60CDAAA33E0B5D20"): bytes.fromhex(
        "a21639ced1531ae99d8229a2d5b44c3c5243d73ea4a07099db98ef82c0fd7f5a21ffdce5adc77a3b"
    ),
    (KeyFamily.S7_1500, "65227E2580029B7F"): bytes.fromhex(
        "c249c5135787859bc1e0f475798f134dec36a3df81cdc47d07d1f03060ab0311547f4ba090d7a487"
    ),
    (KeyFamily.S7_1500, "6BA412F7F1D965AA"): bytes.fromhex(
        "576516d41c3254e9bb392215cad08f23b3ffb6bc1c588edbb424c44397b068af316f34ad26bf13fc"
    ),
    (KeyFamily.S7_1500, "99E4632334CC7993"): bytes.fromhex(
        "3078a83781ca537d29476e26dccd3ab8fb707348c5af98054b4432c89f3601e4be66be574c875967"
    ),
    (KeyFamily.S7_1500, "ACD68E9BF9901F8B"): bytes.fromhex(
        "4c7546b7f80fa1938f22db3e90df57a3cad9369afdbd7f51464b95cf62b8e7ce0aeb0cef1681110f"
    ),
    (KeyFamily.S7_1500, "C4F47B876DA76D52"): bytes.fromhex(
        "67afc52ad2b7e8d81fd5d56b603ff64cb7973904775f5b0f1a8baa6e3b632274809e51a35e67aba0"
    ),
    (KeyFamily.S7_1500, "D3F9CD55A57FE4EB"): bytes.fromhex(
        "cea2b01f2ec599f21bd602edfd168291df355e1b127c4b1313c2d601ab0c0f4f0e65119996643084"
    ),
    (KeyFamily.S7_1500, "E69E7A996524AFAC"): bytes.fromhex(
        "f0ee32aa65f7169c09df3f75cea9bcdb8e1b0f0c90fac0ab19c3dfc1c08bb85ec60773cdef8f524e"
    ),
    # Family 1 — S7-1200 (40-byte keys)
    (KeyFamily.S7_1200, "A95850575DF7B3DE"): bytes.fromhex(
        "dead01d78404e753f0804d1038ebd16cef9788ccc3c78a972c978ce7efd3baf5002cb03e4fce1128"
    ),
    (KeyFamily.S7_1200, "AC9BE476CB324E65"): bytes.fromhex(
        "6c71ed8fcc1ae94172040a14b8b1af7501b81e4cb99937491691075109300866557136c8ae848cad"
    ),
    (KeyFamily.S7_1200, "BD426B091F08731A"): bytes.fromhex(
        "e0e1f04a5ca3f90148178689bd0c930ab9db867b4f0ab109623959aa32316b7880ed1b4f9a9b189f"
    ),
    # Family 3 — PlcSim (64-byte keys)
    (KeyFamily.PLCSIM, "09013727CCBFBF3C"): bytes.fromhex(
        "2b5d9a1aec74c6cefa5fab75edd0ea202d5bff1341de87c1b6f066d291ba08714d6689ab229e147556eeac59a8a157f7b1e7c1d5c12e4eb03cb11a810757f644"
    ),
    (KeyFamily.PLCSIM, "4964E2F77A386F64"): bytes.fromhex(
        "5ede4c30e9bd71c9c416bc43aeda7ad4e8e64a19a061847e7f6f74524fe9aaf917a8c4476085dc0af4ac2f291cd83ce422f1409ee8c23a95524e3ec344caf0b6"
    ),
    (KeyFamily.PLCSIM, "5A9B6B015F48D284"): bytes.fromhex(
        "eca6d799ddf03eaadd16b5d7245331e426c9e6ba8997877a7394f3286532a6b053e4229818085223432483fba4d5c43bd6c354c10febc903908ed271697f39e9"
    ),
    (KeyFamily.PLCSIM, "950840E428F7C7FA"): bytes.fromhex(
        "50f39e36c958ea5ec4982a62337c7f7319eb5c0ef501ac18a28416de86882e21640faf05304dc3b99016f2bc98fa732c2e48e7d3be380d11bf292cdf1691bc93"
    ),
    (KeyFamily.PLCSIM, "AE5147B429BBA96C"): bytes.fromhex(
        "ab7f65871080201263d7925c34a8224136ee01164efd5b79f3ca8e12b1a881c17e3264728c49c11b82a62e03b9f309f6ba054048fe9d5d33e2201b59dbefcc5a"
    ),
    (KeyFamily.PLCSIM, "B07654AC9CAA4ACA"): bytes.fromhex(
        "4700db8fa25d791c2a77eec9795d66e3b5f2ba9a59508add510ca9fe8762aa081dff80ea8f730ad4caa0bca7ba92892c691984338eec2047681d958dc5c5086a"
    ),
    (KeyFamily.PLCSIM, "CE331E08538A26B9"): bytes.fromhex(
        "d2a736be8e86ad4d22a43a43fbc531cb1f30f8e35dbe4d934c8cbaeb66db96db2f1a52c59b81ff2845228e1487f02687da14229c0840b1d611cbce698eb5ece3"
    ),
    (KeyFamily.PLCSIM, "D61B355B59D711A9"): bytes.fromhex(
        "166f0ae5b303d53bbadbb2a6268ecb1a4fcdec74f9a05f6596a6add71256b10867aee0214f05ea714f73c06ec0b71445b3eb39c8306f233756cf53653a12e924"
    ),
    (KeyFamily.PLCSIM, "E90B455D3CC46013"): bytes.fromhex(
        "0fb15661f5953df692f3ce717f3a5b6cb70ff7da11ecdd8a27ff38958601292738f24a30c7381cf392ef2492863ee0b383ca816bd46b18e0e82a30b47a414d19"
    ),
}


def parse_fingerprint(fingerprint: str) -> tuple[KeyFamily, str]:
    """Parse a ``"FF:HHHHHHHHHHHHHHHH"`` fingerprint string.

    Args:
        fingerprint: The ``ObjectVariableTypeName`` value the PLC sent
            in its CreateObject response. Always 19 ASCII characters:
            two hex digits, a colon, sixteen hex digits.

    Returns:
        A ``(family, key_id)`` pair where ``key_id`` is the uppercase
        16-hex-digit string after the colon.

    Raises:
        ValueError: If the fingerprint is not the expected shape or
            its family byte is not one of the supported families.
    """
    if len(fingerprint) != 19 or fingerprint[2] != ":":
        raise ValueError(f"Invalid fingerprint shape: {fingerprint!r}")

    try:
        family_value = int(fingerprint[:2], 16)
    except ValueError as e:
        raise ValueError(f"Invalid family in fingerprint: {fingerprint!r}") from e

    try:
        family = KeyFamily(family_value)
    except ValueError as e:
        raise ValueError(f"Unsupported public-key family 0x{family_value:02X} in fingerprint: {fingerprint!r}") from e

    key_id = fingerprint[3:].upper()
    try:
        bytes.fromhex(key_id)
    except ValueError as e:
        raise ValueError(f"Invalid key id in fingerprint: {fingerprint!r}") from e

    return family, key_id


def get_public_key(fingerprint: str) -> bytes:
    """Look up the public-key bytes for a given fingerprint.

    Args:
        fingerprint: The ``"FF:HHHH..."`` value the PLC advertises.

    Returns:
        Raw key bytes — 40 bytes for real PLCs (families 0 and 1),
        64 bytes for PlcSim (family 3).

    Raises:
        ValueError: On a malformed or unsupported-family fingerprint.
        UnknownPublicKeyError: When the family is supported but the
            specific key id is not in the bundled store.
    """
    family, key_id = parse_fingerprint(fingerprint)
    try:
        return _PUBLIC_KEYS[(family, key_id)]
    except KeyError:
        raise UnknownPublicKeyError(fingerprint) from None
