"""
The :code:`__main__` module is used as an entrypoint when calling the module from the terminal using python -m flag.
It contains functions providing a comandline interface to the server module.

Its :code:`main()` function is also exported as an consol-entrypoint.
"""

import logging

try:
    import click
except ImportError as e:
    print(e)
    print("Try using 'pip install python-snap7[cli]'")
    exit()

from snap7 import __version__
from snap7.common import load_library
from snap7.server import mainloop

logger = logging.getLogger("Snap7.Server")


@click.command()
@click.option("-p", "--port", default=1102, help="Port the server will listen on.")
@click.option(
    "--dll",
    hidden=True,
    type=click.Path(exists=True, file_okay=True, dir_okay=False, resolve_path=True),
    help="Path to the snap7 DLL (for emergencies if it can't be put on PATH).",
)
@click.option("-v", "--verbose", is_flag=True, help="Also print debug-output.")
@click.version_option(__version__)
@click.help_option("-h", "--help")
def main(port, dll, verbose):
    """Start a S7 dummy server with some default values."""

    # setup logging
    if verbose:
        logging.basicConfig(format="[%(levelname)s]: %(message)s", level=logging.DEBUG)
    else:
        logging.basicConfig(format="[%(levelname)s]: %(message)s", level=logging.INFO)

    # normally the snap7.dll should be on PATH and will be loaded automatically by the mainloop,
    # but for emergencies, we allow the DLL's location to be passed as an argument and load it here
    if dll:
        load_library(dll)

    # start the server mainloop
    mainloop(port, init_standard_values=True)


if __name__ == "__main__":
    main()
