"""
The :code:`__main__` module is used as an entrypoint when calling the module from the terminal using python -m flag.
It contains functions providing a command-line interface to the server module.

Its :code:`main()` function is also exported as a console-entrypoint.
"""

import logging

try:
    import click
except ImportError:
    print("Try using 'pip install python-snap7[cli]'")
    raise

from snap7 import __version__
from snap7.server import mainloop

logger = logging.getLogger("Snap7.Server")


@click.command()
@click.option("-p", "--port", default=1102, help="Port the server will listen on.")
@click.option("-v", "--verbose", is_flag=True, help="Also print debug-output.")
@click.version_option(__version__)
@click.help_option("-h", "--help")
def main(port: int, verbose: bool) -> None:
    """Start a S7 dummy server with some default values."""

    # setup logging
    if verbose:
        logging.basicConfig(format="[%(levelname)s]: %(message)s", level=logging.DEBUG)
    else:
        logging.basicConfig(format="[%(levelname)s]: %(message)s", level=logging.INFO)

    # start the server mainloop
    mainloop(port, init_standard_values=True)


if __name__ == "__main__":
    main()
