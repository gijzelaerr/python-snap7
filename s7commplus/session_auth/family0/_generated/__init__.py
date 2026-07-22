"""Machine-transpiled monolith transforms and constant tables.

DO NOT EDIT — regenerate via ``tools/transpile_harpo_monolith.py``.

These modules are mechanically transpiled from the C# sources in
``HarpoS7.Family0.Monoliths`` (MIT, https://github.com/bonk-dev/HarpoS7).
Each ``monolithN.execute(dst, src)`` is a straight-line uint32 arithmetic
port of the corresponding ``MonolithN.Execute`` method, verified byte-for-
byte against the upstream test vectors.

The transforms are inherently opaque — they implement a proprietary
permutation cipher reverse-engineered from Siemens' ``OMSp_core_managed.dll``.
See ``ARCHITECTURE.md`` in the parent ``session_auth/`` package for how they
fit into the authentication flow.

Subpackages:
    nine/    Monolith9 parts (split for Python's parser limits)
    ten/     Monolith10 parts (split for Python's parser limits)
    data/    Binary lookup tables and constant arrays
"""
