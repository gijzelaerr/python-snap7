"""
MicroPython / CircuitPython compatibility layer.

This module detects the Python runtime and provides shims for features
that differ between CPython and MicroPython. It is imported by core
modules that need to work on both platforms.

Compatibility status of python-snap7 core modules:

    Module              Status      Notes
    ----------------    --------    ------------------------------------------
    connection.py       OK          Uses socket, struct, enum, logging -- all
                                    available in MicroPython.
    s7protocol.py       OK          Uses struct, enum, logging, datetime.
    datatypes.py        OK          Uses struct, enum only.
    error.py            SHIM        Uses functools.cache (not in MicroPython).
    client.py           PARTIAL     Imports ctypes (c_int, Array, memmove) for
                                    legacy async helpers. Core read/write ops
                                    do not need ctypes.
    type.py             BLOCKED     Heavily uses ctypes.Structure for data
                                    types (BlocksList, S7CpuInfo, etc.).
    util/getters.py     OK          Uses struct, datetime only.
    util/setters.py     OK          Uses struct, datetime, re only.
    util/db.py          OK          Pure Python data handling.

Known blockers and shims provided here:

1. ``functools.cache`` -- not available in MicroPython.  We provide a
   no-op fallback (the decorated function still works, just without
   memoisation).

2. ``ctypes`` -- not available in MicroPython.  The core protocol stack
   (connection, s7protocol, datatypes) does **not** use ctypes. Only
   ``type.py`` and the async helpers in ``client.py`` depend on it.
   On MicroPython the high-level ``type.py`` structures (BlocksList,
   S7CpuInfo, ...) are unavailable; users should work with raw
   ``bytearray`` / ``dict`` results instead.

3. ``typing`` -- not available in MicroPython, but only used for type
   annotations which are ignored at runtime.  No shim needed.

4. ``types.TracebackType`` -- imported in ``connection.py`` for
   ``__exit__`` signature.  Not available in MicroPython but only used
   in annotations.

5. ``datetime.timedelta`` -- available in CPython but only partially in
   MicroPython.  The core protocol stack uses ``datetime.datetime``
   (available in MicroPython) for clock get/set.  Utility getters/setters
   that use ``timedelta`` will not work on MicroPython without the
   ``micropython-datetime`` package.

6. ``importlib.metadata`` -- used in ``__init__.py`` for version detection.
   Not available in MicroPython.

7. PEP 585 built-in generics (``dict[str, Any]``, ``tuple[...]``) -- used
   in a few type annotations.  These are syntax-level and only evaluated
   at runtime if introspected; MicroPython ignores annotations so this is
   fine.

Usage::

    from snap7.compat import MICROPYTHON, cache

"""

import sys

#: True when running on MicroPython (or CircuitPython).
MICROPYTHON: bool = sys.implementation.name in ("micropython", "circuitpython")

# ---------------------------------------------------------------------------
# functools.cache shim
# ---------------------------------------------------------------------------
try:
    from functools import cache
except ImportError:
    # MicroPython: provide a transparent pass-through (no memoisation).
    from typing import TypeVar, Callable

    _F = TypeVar("_F", bound=Callable[..., object])

    def cache(func: _F) -> _F:  # type: ignore[misc]
        """No-op cache decorator for MicroPython compatibility."""
        return func


# ---------------------------------------------------------------------------
# ctypes availability flag
# ---------------------------------------------------------------------------
try:
    import ctypes as _ctypes  # noqa: F401

    HAS_CTYPES: bool = True
except ImportError:
    HAS_CTYPES = False
