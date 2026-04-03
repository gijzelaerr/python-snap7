"""S7 data type conversion utilities.

Re-exports all getter and setter helpers from :mod:`snap7.util` so that
users of the ``s7`` package do not need to import ``snap7`` directly::

    from s7.util import get_bool, set_bool
"""

from snap7.util import *  # noqa: F401, F403
from snap7.util import __all__  # noqa: F401
