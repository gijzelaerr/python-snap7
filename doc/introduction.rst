Introduction
============

python-snap7 is a pure Python S7 communication library for interfacing
natively with Siemens S7 PLCs. The library implements the complete S7
protocol stack including TPKT (RFC 1006), COTP (ISO 8073), and S7
protocol layers.

python-snap7 requires Python 3.10+ and runs on Windows, macOS and Linux
without any native dependencies.

.. note::

   **Version 3.0 is a complete rewrite.** Previous versions of python-snap7
   were a wrapper around the C snap7 shared library. Starting with version 3.0,
   the entire protocol stack is implemented in pure Python. This eliminates the
   need for platform-specific shared libraries and makes the library portable to
   any platform that runs Python.

   If you experience issues, please report them on the
   `issue tracker <https://github.com/gijzelaerr/python-snap7/issues>`_ with a
   clear description and the version you are using. As a workaround, you can
   install the last pre-3.0 release with ``pip install "python-snap7<3"``.

The project development is centralized on `github <https://github.com/gijzelaerr/python-snap7>`_.
