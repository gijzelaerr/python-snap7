About
=====

This is a ctypes based python wrapper for snap7. Snap7 is an open source,
32/64 bit, multi-platform Ethernet communication suite for interfacing natively
with Siemens S7 PLCs.

python-snap7 is still a work in progress. basic functionality is there,
but at the moment only Python 2.7 is supported.

.. image:: https://travis-ci.org/gijzelaerr/python-snap7.png?branch=master 
  :target: https://travis-ci.org/gijzelaerr/python-snap7


Installation
============

First install the snap7 library. You can download the source from the
`snap7 website <http://snap7.sourceforge.net/>`_ and compile it, or if you use
Ubuntu you can use the
`Ubuntu packages <https://launchpad.net/~gijzelaar/+archive/snap7>`_ we created.

Next you can install the snap7 python rapper by running::

    $ pip install python-snap7


or when you install from source::

    $ python setup.py install



credits
=======

- Gijs Molenaar
- Stephan Preeker

Special thanks to
=================
 - Davide Nardella for creating snap7
 - Thomas Hergenhahn for his libnodave.
 - Thomas W for his S7comm wireshark plugin
