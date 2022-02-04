"""
The Snap7 Python library.
"""
import pkg_resources

import snap7.client as client
import snap7.common as common
import snap7.error as error
import snap7.logo as logo
import snap7.server as server
import snap7.types as types
import snap7.util as util

__all__ = ['client', 'common', 'error', 'logo', 'server', 'types', 'util']

try:
    __version__ = pkg_resources.require("python-snap7")[0].version
except pkg_resources.DistributionNotFound:
    __version__ = "0.0rc0"
