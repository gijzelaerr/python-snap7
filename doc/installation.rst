Installation
============

python-snap7 is a pure Python package with no native dependencies. Install it
using pip::

  $ pip install python-snap7

If you want to use the CLI interface for running an emulator, install it with::

  $ pip install "python-snap7[cli]"

That's it! No native libraries or platform-specific setup is required. This works
on any platform that supports Python 3.10+, including ARM, Alpine Linux, and other
environments where the old C library was hard to install.

Upgrading from 2.x
-------------------

Version 3.0 is a complete rewrite. Previous versions wrapped the C snap7 shared
library; version 3.0 implements the entire protocol stack in pure Python. While
the public API is largely the same, this is a fundamental change under the hood.

If you experience issues after upgrading:

1. Please report them on the `issue tracker <https://github.com/gijzelaerr/python-snap7/issues>`_
   with a clear description and your version (``python -c "import snap7; print(snap7.__version__)"``).
2. As a workaround, pin to the last pre-3.0 release::

     $ pip install "python-snap7<3"

   The latest stable pre-3.0 release is version 2.1.0.
