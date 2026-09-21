Installation
============

The core python-snap7 package is pure Python and has no runtime dependencies.
Install it with pip::

  $ pip install python-snap7

Optional features
-----------------

Install only the extras needed by your application:

.. list-table::
   :header-rows: 1
   :widths: 20 30 50

   * - Extra
     - Install command
     - Purpose
   * - ``cli``
     - ``pip install "python-snap7[cli]"``
     - The ``s7`` command for reading, writing, inspecting, and serving.
   * - ``demo``
     - ``pip install "python-snap7[demo]"``
     - Live demo server with host metrics and terminal display.
   * - ``discovery``
     - ``pip install "python-snap7[discovery]"``
     - PROFINET DCP device discovery.
   * - ``ppi``
     - ``pip install "python-snap7[ppi]"``
     - Experimental S7-200 serial PPI support via pySerial.
   * - ``doc``
     - ``pip install "python-snap7[doc]"``
     - Sphinx and the theme used to build this documentation.

Extras can be combined::

  $ pip install "python-snap7[cli,discovery,ppi]"

No Snap7 shared library or platform-specific binary is required. Optional
dependencies may have their own platform requirements; for example, PPI needs a
serial interface and discovery needs access to a supported network interface.

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

   The latest stable pre-3.0 release is version 2.1.1.
