.. image:: https://img.shields.io/pypi/v/python-snap7?label=python-snap7&link=https%3A%2F%2Fpypi.org%2Fproject%2Fpython-snap7%2F
   :alt: PyPI - Version

.. image:: https://img.shields.io/github/actions/workflow/status/gijzelaerr/python-snap7/build-and-test-amd64.yml?branch=master
   :alt: GitHub Actions Workflow Status

.. image:: https://img.shields.io/github/issues/gijzelaerr/python-snap7
   :alt: GitHub Issues or Pull Requests

.. image:: https://img.shields.io/pypi/pyversions/python-snap7
   :alt: PyPI - Python Version

.. image:: https://img.shields.io/github/discussions/gijzelaerr/python-snap7
   :alt: GitHub Discussions

.. image:: https://img.shields.io/pypi/l/python-snap7
   :alt: PyPI - License

python-snap7
===========


This is a ctypes-based Python wrapper for snap7. Snap7 is an open-source,
32/64 bit, multi-platform Ethernet communication suite for interfacing natively
with Siemens S7 PLCs.

Python-snap7 is tested with Python 3.9+, on Windows, Linux and OS X.

The full documentation is available on `Read The Docs <https://python-snap7.readthedocs.io/en/latest/>`_.

Installation
============

Wheel installation::

   $ pip install python-snap7

Available on :

- Windows
- Mac OS X
- GNU/Linux

Compatible architectures :

- Intel/AMD 32/64
- ARM64

Usage
====

The python-snap7 library provides a comprehensive set of tools for communicating with Siemens S7 PLCs over Ethernet. It offers a variety of modules, each catering to specific communication needs, including:

- **Client**: The client module establishes a connection to a Siemens S7 PLC, enabling data read and write operations. It's ideal for applications that directly interact with PLC data.
- **Server**: The server module turns a Python application into an S7 PLC server, allowing it to receive data from and send data to S7 PLCs. This is useful for building centralized control or data acquisition systems.
- **Partner**: The partner module facilitates communication between two S7 PLCs, enabling data exchange and coordination between them. This module is particularly valuable for implementing distributed control systems.

If you aren't familiar with S7 Protocol/Function, see `Snap7 documentation Snap7 communication <https://snap7.sourceforge.net/>`_

There is a **utils** module provides a collection of utility functions for working with PLC data, memory areas, and communication protocols. It simplifies data manipulation and conversion tasks.

For more information, please read the `online installation documentation <https://python-snap7.readthedocs.io/en/latest/installation.html>`_.


How to Contribute
================

There are many ways to contribute to the python-snap7 project. Here are a few ideas:

- **Report bugs**: If you find a bug in the library, please report it on the project's issue tracker.
- **Fix bugs**: If you are able to fix a bug, please submit a pull request with your fix.
- **Write documentation**: The library's documentation could always be improved. If you are willing to write documentation, please contact the project maintainers.
- **Write new features**: If you have a new feature that you would like to see added to the library, please submit a proposal on the project's mailing list.`

See `Q&A <https://python-snap7.readthedocs.io/en/latest/development.html>`_.

Credits
==========

python-snap7 is created by:

- Gijs Molenaar (gijs at pythonic dot nl)
- Stephan Preeker (stephan at preeker dot net)

Special thanks to:

- Davide Nardella for creating `snap7 <https://snap7.sourceforge.net/>`_
- Thomas Hergenhahn for his `libnodave <https://libnodave.sourceforge.io/>`_
- Thomas W for his S7comm wireshark plugin
- Fabian Beitler and Nikteliy for their contributions towards the 1.0 release
- Lautaro Nahuel Dapino for his contributions.

