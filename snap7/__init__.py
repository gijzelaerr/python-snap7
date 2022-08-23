"""
The Snap7 Python library.
"""
import pkg_resources

from . import client
from . import common
from . import error
from . import logo
from . import server
from . import types
from . import util

__all__ = ['client', 'common', 'error', 'logo', 'server', 'types', 'util']

try:
    __version__ = pkg_resources.require("python-snap7")[0].version
except pkg_resources.DistributionNotFound:
    __version__ = "0.0rc0"
