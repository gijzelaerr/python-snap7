
from ctypes import cdll
from ctypes.util import find_library

lib_location = find_library('snap7')
if not lib_location:
    msg = "can't find snap7 library. If installed, try running ldconfig"
    raise Exception(msg)
clib = cdll.LoadLibrary(lib_location)
