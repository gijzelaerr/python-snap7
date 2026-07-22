# session_auth — S7CommPlus Session Authentication

Python port of [bonk-dev/HarpoS7](https://github.com/bonk-dev/HarpoS7) (MIT),
which is a clean-room re-implementation of the proprietary authentication in
Siemens' `OMSp_core_managed.dll`.

## When is this needed?

V1-initial S7-1200 PLCs (FW < V4.5, no TLS) require a **SessionKey handshake**
in the SetupSession step before they accept data operations. Without it, the PLC
returns an incomplete session and rejects all S7CommPlus requests.

Newer PLCs (V2/V3/TLS) use standard TLS certificates instead and do not need
any of this machinery.

## Authentication flow

```
PLC                                          Client
 │                                              │
 │◄──── CreateObject ───────────────────────────│  V1 framing
 │ response: session_id, public_key_fingerprint │
 │           session_challenge (20 bytes)        │
 │           ServerSessionVersion (Struct 314)   │
 │                                              │
 │  ┌─ Client-side (no network) ──────────────┐ │
 │  │ 1. Look up PLC's public key by          │ │
 │  │    fingerprint (keys.py)                 │ │
 │  │ 2. Generate random key1 (24B), key2     │ │
 │  │    (24B), IV (16B)                       │ │
 │  │ 3. Run Family-0 transforms to produce   │ │
 │  │    180-byte SecurityKeyEncryptedKey blob │ │
 │  │ 4. Derive 24-byte session_key via       │ │
 │  │    HMAC-SHA256(key2, fingerprint ||      │ │
 │  │    challenge)                            │ │
 │  └─────────────────────────────────────────┘ │
 │                                              │
 │◄──── SetupSession ───────────────────────────│  V2 framing
 │  SecurityKey blob (addr 1830)                │
 │  + ServerSessionVersion echo (addr 306)      │
 │                                              │
 │──── response: success ──────────────────────►│
 │                                              │
 │  ══ data operations now work (V3+HMAC) ══    │
 │                                              │
 │◄──── GET_VAR_SUB addr 303 (challenge) ───────│  (optional, only if
 │◄──── SET_VAR_SUB addr 1846 (solved blob) ────│   password provided)
 │                                              │
```

After SetupSession, all data frames use **V3 framing** with HMAC-SHA256
(keyed by the first 24 bytes of the session key). No intermediate
activation sequence is needed — data reads work immediately.

Note: TIA Portal sends SET_VARIABLE attr 323 + finalize reads before
data operations, but this is TIA-specific behavior. The HarpoS7
reference implementation skips it, and V1-initial PLCs reject the
SET_VARIABLE with a connection reset (GH-710).

## Module map

### Orchestration (human-readable)

```
session_auth/
├── __init__.py              Public API re-exports
├── ARCHITECTURE.md          This file
├── keys.py                  Public-key store (fingerprint → 40/64-byte key)
├── key_derivation.py        SHA-256 KDFs (challenge key, seed key+IV, session key)
├── legitimate.py            Post-auth challenge solver (DEADBEEF blob builder)
├── blob_metadata.py         SecurityKeyEncryptedKey blob header/metadata
├── harpo_aes.py             AES-ECB primitives (used by checksum + seed encryption)
├── harpo_aes_ctr.py         Custom AES-CTR mode (non-standard counter increment)
├── harpo_hash.py            SHA-256-based hash with LUT mixing
├── utils.py                 Key-ID derivation (SHA-256 → 8 bytes)
│
├── family0/
│   ├── __init__.py
│   ├── authenticator.py     RealPlcAuthenticator — top-level blob builder
│   ├── fingerprint.py       8-byte challenge fingerprint (LUT + mutation chain)
│   ├── seed_transform.py    Encrypted seed generation (monolith chain)
│   ├── pre_seed_transform.py  Random key → pre-seed via Monolith9
│   ├── key_derivation_transform.py  Pre-seed → 3 AES keys via Monolith9/10
│   ├── checksum_transform.py  AES-ECB checksum of encrypted blocks
│   ├── lut_generator.py     Lookup table for harpo_hash
│   ├── transform7.py        Core EC point multiplication (monolith wrappers)
│   ├── transform12.py       Opcode-driven BigInt dispatcher
│   ├── transform13.py       3×24-byte BigInt output via Monolith9/10
│   ├── big_int_operations.py  192-bit arithmetic (add, sub, mul, square)
│   ├── big_int_transforms.py  BigInt higher-level ops
│   └── monolith_wrappers.py  WithCopy adapters for Monolith3-7
```

### Machine-transpiled (do not edit)

```
│   └── _generated/
│       ├── __init__.py
│       ├── monolith1.py … monolith11.py   Permutation ciphers (~30K lines)
│       ├── nine/part1.py … part11.py      Monolith9 parts (~50K lines)
│       ├── ten/part1.py … part3.py        Monolith10 parts (~15K lines)
│       └── data/
│           ├── __init__.py                Binary data loaders
│           ├── _constants.py              Python constant arrays
│           ├── fp_data1.bin, fp_data2.bin  Fingerprint lookup tables
│           ├── transform12_metadata.bin   Transform12 opcode tape
│           └── transform12_big_int_data.bin  BigInt constant table
```

The `_generated/` modules are transpiled from HarpoS7's C# via
`tools/transpile_harpo_monolith.py`. Each `monolithN.execute(dst, src)` is a
straight-line uint32 arithmetic function verified byte-for-byte against upstream
test vectors. They implement a proprietary permutation cipher and cannot be
meaningfully simplified — the algorithm is designed to resist analysis.

## How the blob is built (authenticator.py)

```
RealPlcAuthenticator(key1=random_24B, key2=random_24B)
│
├── write_seed(dst, public_key)
│   ├── PreSeedTransform(key1)           →  60-byte pre-seed
│   ├── KeyDerivationTransform(pre-seed) →  3 × 16-byte keys
│   ├── SeedTransform(key1, public_key)  →  60-byte encrypted seed
│   │   ├── Transform7 (EC scalar mul)
│   │   ├── Monolith1.Loop → Monolith2 → Monolith8
│   │   └── Transform13 → Monolith11
│   └── AES-ECB encrypt seed with derived key
│
├── encrypt_full_blocks(dst, challenge)
│   └── HarpoAesCtr(challenge_key, key2[:16])
│       └── AES-CTR encrypt challenge blocks + checksum
│
└── encrypt_final_block(dst)
    └── HarpoAesCtr final block + PKCS-style padding
```

## References

- [HarpoS7](https://github.com/bonk-dev/HarpoS7) — MIT, C# clean-room implementation
- [lircy/S7CommPlusV3Driver](https://github.com/lircy/S7CommPlusV3Driver) — ships HarpoS7 as precompiled native DLLs
- Cheng Lei et al., "The Spear to Break the Security Wall of S7CommPlus", Black Hat EU 2017
- Biham, Bitan et al., "Rogue7: Rogue Engineering Station Attacks on S7 Simatic PLCs", Black Hat USA 2019
