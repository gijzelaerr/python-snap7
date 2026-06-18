Connecting to PLCs
==================

This page shows how to connect to different Siemens PLC models using
python-snap7. All examples use the recommended ``s7`` package, which works
with every supported PLC model.

.. contents:: On this page
   :local:
   :depth: 2


Rack/Slot Reference
-------------------

.. list-table::
   :header-rows: 1
   :widths: 20 10 10 60

   * - PLC Model
     - Rack
     - Slot
     - Notes
   * - S7-300
     - 0
     - 2
     -
   * - S7-400
     - 0
     - 3
     - May vary with multi-rack configurations
   * - S7-1200
     - 0
     - 1
     - PUT/GET access must be enabled in TIA Portal (or use S7CommPlus)
   * - S7-1500
     - 0
     - 1
     - PUT/GET access must be enabled in TIA Portal (or use S7CommPlus)
   * - S7-200 / Logo
     - --
     - --
     - Use ``set_connection_params`` with TSAP addressing (legacy ``snap7`` package)

.. warning::

   S7-1200 and S7-1500 PLCs ship with PUT/GET communication disabled by
   default. When using ``s7.Client``, the library automatically tries the
   S7CommPlus protocol first, which does not require PUT/GET to be enabled.
   If you need to use the legacy protocol, enable PUT/GET in TIA Portal
   under the CPU properties. See :doc:`tia-portal-config` for step-by-step
   instructions.


S7-300
------

.. code-block:: python

   from s7 import Client

   client = Client()
   client.connect("192.168.1.10", 0, 2)

S7-400
------

.. code-block:: python

   from s7 import Client

   client = Client()
   client.connect("192.168.1.10", 0, 3)

S7-1200 / S7-1500
------------------

.. code-block:: python

   from s7 import Client

   client = Client()
   client.connect("192.168.1.10", 0, 1)
   print(client.protocol)  # Protocol.S7COMMPLUS or Protocol.LEGACY

The client automatically tries S7CommPlus first and falls back to legacy S7
when needed. You can also force a specific protocol:

.. code-block:: python

   from s7 import Client, Protocol

   client = Client()
   # Force legacy S7 only (requires PUT/GET enabled)
   client.connect("192.168.1.10", 0, 1, protocol=Protocol.LEGACY)

   # Force S7CommPlus (raises on failure)
   client.connect("192.168.1.10", 0, 1, protocol=Protocol.S7COMMPLUS)

See :doc:`API/client` for details on TLS and password authentication.

S7CommPlus over TLS (V2/V3, TIA Portal V17+)
---------------------------------------------

S7-1500 firmware ≥ V2.9 and S7-1200 firmware ≥ V4.5 negotiate
S7CommPlus V2 or V3, which transports the protocol inside a TLS 1.3
session. Pass ``use_tls=True`` to ``connect`` to activate it:

.. code-block:: python

   from s7 import Client, Protocol

   client = Client()
   client.connect(
       "192.168.1.10", rack=0, slot=1,
       protocol=Protocol.S7COMMPLUS,
       use_tls=True,
   )
   data = client.db_read(1, 0, 4)
   client.disconnect()

The client wraps the ISO-on-TCP socket with TLS 1.3 between the
``InitSSL`` exchange and the ``CreateObject`` request. By default the
PLC's certificate is not verified — fine for development, not fine in
production. To verify the PLC against a CA bundle, pass ``tls_ca``:

.. code-block:: python

   client.connect(
       "192.168.1.10", rack=0, slot=1,
       protocol=Protocol.S7COMMPLUS,
       use_tls=True,
       tls_ca="/path/to/plc-ca.pem",
   )

If the PLC requires mutual TLS (client-side certificate), supply
``tls_cert`` and ``tls_key`` as well.

The ``cryptography`` package is required for TLS support. Install
with the ``s7commplus`` extra:

.. code-block:: bash

   pip install 'python-snap7[s7commplus]'

.. note::

   Older S7-1200 firmware (FW < 4.5) negotiates V1 of the S7CommPlus
   protocol, which predates TLS and uses a different proprietary
   handshake. ``Client(...)`` falls back transparently to legacy
   PUT/GET on those PLCs (``db_read`` / ``db_write`` work);
   ``browse()`` and other CommPlus-only operations are not yet
   supported on those firmwares — see issue #710.

TLS handshake fails on OpenSSL 3.5+ (post-quantum key share)
-------------------------------------------------------------

On systems with **OpenSSL ≥ 3.5** (e.g. Debian 13 and other recent
distributions) the TLS 1.3 ``ClientHello`` advertises a post-quantum
hybrid key-exchange group, ``X25519MLKEM768``, by default. Its key
share is roughly 1.2 KB, and the S7-1500's TLS stack rejects the
oversized ``ClientHello`` — it drops the connection mid-handshake, so
``connect(use_tls=True)`` fails with a *connection reset by peer*.

The PLC mandates TLS 1.3 (it refuses TLS 1.2 outright), and CPython's
``ssl`` module exposes no API to restrict the TLS 1.3
``supported_groups`` list. The fix is to restrict the offered groups
through OpenSSL's own configuration — via the ``OPENSSL_CONF``
environment variable — to the classic ECDHE curves that every
S7-1200/1500 supports.

1. Create an OpenSSL configuration file, e.g. ``s7-openssl.cnf``:

   .. code-block:: ini

      # Restrict the TLS key-exchange groups to classic ECDHE curves so the
      # ClientHello stays small enough for the S7-1500 to accept.
      openssl_conf = openssl_init

      [openssl_init]
      ssl_conf = ssl_configuration

      [ssl_configuration]
      system_default = system_default_sect

      [system_default_sect]
      Groups = x25519:secp256r1:secp384r1

2. Point ``OPENSSL_CONF`` at it **before** the Python process starts.
   OpenSSL reads this configuration once, when it initialises, so
   setting the variable from inside Python (e.g. via ``os.environ``)
   after ``ssl`` is imported is too late — it must be set in the
   environment:

   .. code-block:: bash

      # for a single run
      OPENSSL_CONF=/path/to/s7-openssl.cnf python your_script.py

      # or for the whole shell session
      export OPENSSL_CONF=/path/to/s7-openssl.cnf

With the groups restricted to classic curves, the TLS 1.3 handshake no
longer offers ``X25519MLKEM768`` and the S7-1500 completes it normally.

.. note::

   This only affects OpenSSL ≥ 3.5. On older OpenSSL releases the
   default key-exchange groups are already classic ECDHE curves, so no
   extra configuration is needed.

PLC Password Authentication
----------------------------

If the PLC has a password configured (``Full access (no protection)``
disabled in TIA Portal), call ``authenticate`` after ``connect``:

.. code-block:: python

   from s7 import Client, Protocol

   client = Client()
   client.connect(
       "192.168.1.10", rack=0, slot=1,
       protocol=Protocol.S7COMMPLUS,
       use_tls=True,
   )
   client.authenticate(password="hunter2")
   data = client.db_read(1, 0, 4)

Authentication requires TLS to be active (``use_tls=True``). The
client auto-detects whether the PLC firmware uses the legacy SHA-1
challenge or the newer AES-256-CBC challenge. For accounts with a
username (TIA Portal V17+ user-based access control), pass it
explicitly:

.. code-block:: python

   client.authenticate(password="hunter2", username="operator")

S7-200 / Logo (TSAP Connection)
--------------------------------

S7-200 and Logo PLCs require TSAP addressing via the legacy ``snap7`` package:

.. code-block:: python

   import snap7

   client = snap7.Client()
   client.set_connection_params("192.168.1.10", 0x1000, 0x2000)
   client.connect("192.168.1.10", 0, 0)

Using a Non-Standard Port
--------------------------

.. code-block:: python

   from s7 import Client

   client = Client()
   client.connect("192.168.1.10", 0, 1, tcp_port=1102)

Routing (Multi-Subnet Access)
------------------------------

.. warning::

   Routing support is experimental and may change in future versions.

When the target PLC sits on a different subnet behind a gateway PLC, use
``connect_routed`` to let the gateway forward the connection:

.. code-block:: python

   import snap7

   client = snap7.Client()
   client.connect_routed(
       host="192.168.1.1",       # gateway PLC address
       router_rack=0,            # gateway rack
       router_slot=2,            # gateway slot
       subnet=0x0001,            # target subnet ID
       dest_rack=0,              # target PLC rack
       dest_slot=3,              # target PLC slot
   )
   data = client.db_read(1, 0, 4)
   client.disconnect()

Legacy ``snap7`` Package
-------------------------

If you have existing code using ``snap7.Client``, it continues to work
unchanged:

.. code-block:: python

   import snap7

   client = snap7.Client()
   client.connect("192.168.1.10", 0, 1)
