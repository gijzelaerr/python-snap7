"""S7CommPlus session-key authentication primitives.

This subpackage is a Python port of the legacy-challenge half of
`bonk-dev/HarpoS7 <https://github.com/bonk-dev/HarpoS7>`_ (MIT-licensed),
which itself is a clean-room re-implementation of the proprietary
authentication algorithm in Siemens' ``OMSp_core_managed.dll``.

The legacy-challenge handshake is what V1-initial S7-1200 firmware
(and pre-V17 TIA Portal) require for full S7CommPlus operation —
without it, ``browse()`` and other CommPlus data ops fail.

This first slice ports only the public-key store. Subsequent slices
will add the AES/SHA primitives, the proprietary "monolith" transforms,
and the auth orchestration that produces the 216-byte
``SecurityKeyEncryptedKey`` blob.

References:

- HarpoS7: https://github.com/bonk-dev/HarpoS7 (MIT)
- Cheng Lei et al. "The spear to break the security wall of S7CommPlus",
  Black Hat EU 2017.
- Biham, Bitan et al. "Rogue7", Black Hat USA 2019.
"""

from .blob_metadata import (
    ENCRYPTED_BLOB_LENGTH_PLCSIM,
    ENCRYPTED_BLOB_LENGTH_REAL_PLC,
    get_blob_length,
    get_public_key_flags,
    get_symmetric_key_flags,
    write_metadata,
)
from .key_derivation import (
    derive_challenge_encryption_key,
    derive_legitimation_challenge_key,
    derive_seed_encryption_key_and_iv,
)
from .keys import (
    KeyFamily,
    PUBLIC_KEY_LENGTH_REAL_PLC,
    PUBLIC_KEY_LENGTH_PLCSIM,
    UnknownPublicKeyError,
    get_public_key,
    parse_fingerprint,
)
from .utils import KEY_ID_LENGTH, derive_key_id

__all__ = [
    "ENCRYPTED_BLOB_LENGTH_PLCSIM",
    "ENCRYPTED_BLOB_LENGTH_REAL_PLC",
    "KeyFamily",
    "KEY_ID_LENGTH",
    "PUBLIC_KEY_LENGTH_REAL_PLC",
    "PUBLIC_KEY_LENGTH_PLCSIM",
    "UnknownPublicKeyError",
    "derive_challenge_encryption_key",
    "derive_key_id",
    "derive_legitimation_challenge_key",
    "derive_seed_encryption_key_and_iv",
    "get_blob_length",
    "get_public_key",
    "get_public_key_flags",
    "get_symmetric_key_flags",
    "parse_fingerprint",
    "write_metadata",
]
