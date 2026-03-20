.. image:: https://img.shields.io/pypi/v/python-snap7.svg
   :target: https://pypi.org/project/python-snap7/

.. image:: https://img.shields.io/pypi/pyversions/python-snap7.svg
   :target: https://pypi.org/project/python-snap7/

.. image:: https://img.shields.io/github/license/gijzelaerr/python-snap7.svg
   :target: https://github.com/gijzelaerr/python-snap7/blob/master/LICENSE

.. image:: https://github.com/gijzelaerr/python-snap7/actions/workflows/test.yml/badge.svg
   :target: https://github.com/gijzelaerr/python-snap7/actions/workflows/test.yml

.. image:: https://readthedocs.org/projects/python-snap7/badge/
   :target: https://python-snap7.readthedocs.io/en/latest/

.. image:: https://codecov.io/gh/gijzelaerr/python-snap7/branch/master/graph/badge.svg
   :target: https://codecov.io/gh/gijzelaerr/python-snap7

About
=====

Python-snap7 is a pure Python S7 communication library for interfacing with Siemens S7 PLCs.

The name "python-snap7" is historical — the library originally started as a Python wrapper
around the `Snap7 <http://snap7.sourceforge.net/>`_ C library. As of version 3.0, the C
library is no longer used, but the name is kept for backwards compatibility.

Python-snap7 is tested with Python 3.10+, on Windows, Linux and OS X.

The full documentation is available on `Read The Docs <https://python-snap7.readthedocs.io/en/latest/>`_.


Version 3.0 - Pure Python Rewrite
==================================

Version 3.0 is a ground-up rewrite of python-snap7. The library no longer wraps the
C snap7 shared library — instead, the entire S7 protocol stack (TPKT, COTP, and S7)
is now implemented in pure Python. This is a **breaking change** from all previous
versions.

**Why this matters:**

* **Portability**: No more platform-specific shared libraries (`.dll`, `.so`, `.dylib`).
  python-snap7 now works on any platform that runs Python — including ARM, Alpine Linux,
  and other environments where the C library was difficult or impossible to install.
* **Easier installation**: Just ``pip install python-snap7``. No native dependencies,
  no compiler toolchains, no manual library setup.
* **Easier to extend**: New features and protocol support can be added directly in Python.

**If you experience issues with 3.0:**

1. Please report them on the `issue tracker <https://github.com/gijzelaerr/python-snap7/issues>`_
   with a clear description of the problem and the version you are using
   (``python -c "import snap7; print(snap7.__version__)"``).
2. As a workaround, you can pin to the last pre-3.0 release::

       $ pip install "python-snap7<3"

   The latest stable pre-3.0 release is version 2.1.0. Documentation for pre-3.0
   versions is available at `Read The Docs <https://python-snap7.readthedocs.io/en/v2/>`_.


Installation
============

Install using pip::

   $ pip install python-snap7

No native libraries or platform-specific dependencies are required — python-snap7 is a pure Python package that works on all platforms.
