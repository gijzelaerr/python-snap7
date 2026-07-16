"""Alias for the ``snap7`` package.

``s7`` re-exports everything from ``snap7`` so that either name works::

    from s7 import Client          # same as: from snap7 import Client
    from s7.type import Area       # same as: from snap7.type import Area

This alias exists as a transitional step toward retiring the ``snap7``
name. For S7CommPlus (S7-1200/1500), use ``s7commplus`` instead.
"""

import importlib
import sys

import snap7 as snap7  # noqa: F401

from snap7 import *  # noqa: F403
from snap7 import __all__ as __all__, __version__ as __version__

_SUBMODULES = [
    "async_client",
    "cli",
    "client",
    "connection",
    "datatypes",
    "demo",
    "discovery",
    "error",
    "log",
    "logo",
    "optimizer",
    "partner",
    "s7protocol",
    "server",
    "tags",
    "type",
    "util",
]

for _name in _SUBMODULES:
    _fqn = f"s7.{_name}"
    if _fqn not in sys.modules:
        try:
            _mod = importlib.import_module(f"snap7.{_name}")
            sys.modules[_fqn] = _mod
        except ImportError:
            pass

del _name, _fqn, _mod, _SUBMODULES
