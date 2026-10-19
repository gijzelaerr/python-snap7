"""
Console entry point for the ``s7`` command.

The CLI depends on the optional ``click`` package (``pip install python-snap7[cli]``). This wrapper checks for it before
importing :mod:`snap7.cli`, so a plain install prints an install hint instead of an ``ImportError`` traceback.
"""

import importlib.util
import sys


def main() -> None:
    if importlib.util.find_spec("click") is None:
        print("The s7 command requires the CLI dependencies. Install them with: pip install python-snap7[cli]", file=sys.stderr)
        sys.exit(1)

    from snap7.cli import main as cli_main

    cli_main()
