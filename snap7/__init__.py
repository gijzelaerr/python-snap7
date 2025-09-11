"""
The Snap7 Python library.
"""

from importlib.metadata import version, PackageNotFoundError

from .client import Client
from .server import Server
from .logo import Logo
from .partner import Partner
from .util.db import Row, DB
from .type import Area, Block, WordLen, SrvEvent, SrvArea

# Pure Python client and server implementation
try:
    from .native_client import Client as PureClient
    from .native_server import Server as PureServer
    _PURE_PYTHON_AVAILABLE = True
except ImportError:
    _PURE_PYTHON_AVAILABLE = False
    PureClient = None  # type: ignore
    PureServer = None  # type: ignore

__all__ = ["Client", "Server", "Logo", "Partner", "Row", "DB", "Area", "Block", "WordLen", "SrvEvent", "SrvArea"]

# Add pure Python implementations to exports if available
if _PURE_PYTHON_AVAILABLE:
    __all__.extend(["PureClient", "PureServer"])


def get_client(pure_python: bool = False):
    """
    Get a client instance using the specified backend.
    
    Args:
        pure_python: If True, use pure Python implementation.
                    If False (default), use ctypes wrapper around Snap7 C library.
                    
    Returns:
        Client instance using the requested backend.
        
    Raises:
        ImportError: If pure Python backend is requested but not available.
        
    Examples:
        >>> # Use default ctypes backend
        >>> client = snap7.get_client()
        
        >>> # Use pure Python backend  
        >>> client = snap7.get_client(pure_python=True)
    """
    if pure_python:
        if not _PURE_PYTHON_AVAILABLE:
            raise ImportError(
                "Pure Python client is not available. "
                "This may be due to missing dependencies in the native module."
            )
        return PureClient()
    else:
        return Client()


def get_server(pure_python: bool = False):
    """
    Get a server instance using the specified backend.
    
    Args:
        pure_python: If True, use pure Python implementation.
                    If False (default), use ctypes wrapper around Snap7 C library.
                    
    Returns:
        Server instance using the requested backend.
        
    Raises:
        ImportError: If pure Python backend is requested but not available.
        
    Examples:
        >>> # Use default ctypes backend
        >>> server = snap7.get_server()
        
        >>> # Use pure Python backend  
        >>> server = snap7.get_server(pure_python=True)
    """
    if pure_python:
        if not _PURE_PYTHON_AVAILABLE:
            raise ImportError(
                "Pure Python server is not available. "
                "This may be due to missing dependencies in the native module."
            )
        return PureServer()
    else:
        return Server()


# Add to exports
__all__.extend(["get_client", "get_server"])

try:
    __version__ = version("python-snap7")
except PackageNotFoundError:
    __version__ = "0.0rc0"
