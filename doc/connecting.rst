Connecting to PLCs
==================

This page shows how to connect to different Siemens PLC models using
python-snap7.

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
     - Use ``set_connection_params`` with TSAP addressing (``s7`` package)

.. warning::

   S7-1200 and S7-1500 PLCs ship with PUT/GET communication disabled by
   default. Use ``s7commplus.Client`` to communicate via S7CommPlus, which
   does not require PUT/GET to be enabled. If you need to use
   ``s7.Client`` (legacy protocol), enable PUT/GET in TIA Portal
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

S7-1200 / S7-1500 (S7CommPlus)
-------------------------------

.. code-block:: python

   from s7commplus import Client

   client = Client()
   client.connect("192.168.1.10")

S7-1200 / S7-1500 (Legacy PUT/GET)
------------------------------------

If PUT/GET access is enabled in TIA Portal, you can also use the legacy
protocol:

.. code-block:: python

   from s7 import Client

   client = Client()
   client.connect("192.168.1.10", 0, 1)

See :doc:`API/client` for details on TLS and password authentication.

S7CommPlus over TLS (V2/V3, TIA Portal V17+)
---------------------------------------------

S7-1500 firmware ≥ V2.9 and S7-1200 firmware ≥ V4.5 negotiate
S7CommPlus V2 or V3, which transports the protocol inside a TLS 1.3
session. Pass ``use_tls=True`` to ``connect`` to activate it:

.. code-block:: python

   from s7commplus import Client

   client = Client()
   client.connect(
       "192.168.1.10",
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
       "192.168.1.10",
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
   protocol, which predates TLS and uses a SessionKey handshake instead.
   The synchronous ``Client`` performs this handshake when ``use_tls`` is
   false; it does not fall back to the classic PUT/GET protocol. V1 support
   is experimental and the asynchronous client currently supports only the
   TLS path. See `issue #710
   <https://github.com/gijzelaerr/python-snap7/issues/710>`_ for the original
   V1 hardware report.

TLS handshake rejected by the PLC (connection reset)
------------------------------------------------------

S7 PLCs have a minimal TLS stack that rejects ``ClientHello`` messages
containing features it does not recognise. Two common causes:

* **Post-quantum key share (OpenSSL ≥ 3.5)** — the default
  ``ClientHello`` advertises the ``X25519MLKEM768`` hybrid group whose
  ~1.2 KB key share the PLC drops.
* **Modern signature algorithms** — OpenSSL advertises Ed25519, Ed448,
  and RSA-PSS variants in the ``signature_algorithms`` extension.
  Instead of ignoring unknown algorithms (as TLS 1.2 requires), the PLC
  treats them as a fatal error and sends a TCP RST.

CPython's ``ssl`` module exposes no API for either the
``supported_groups`` or ``signature_algorithms`` lists. The fix is to
restrict both through OpenSSL's own configuration via the
``OPENSSL_CONF`` environment variable.

1. Create an OpenSSL configuration file, e.g. ``s7-openssl.cnf``:

   .. code-block:: ini

      # Restrict TLS parameters for S7 PLC compatibility.
      openssl_conf = openssl_init

      [openssl_init]
      ssl_conf = ssl_configuration

      [ssl_configuration]
      system_default = system_default_sect

      [system_default_sect]
      # Classic ECDHE curves only — no post-quantum groups.
      Groups = x25519:secp256r1:secp384r1
      # Classic signature algorithms only — no Ed25519, Ed448, or RSA-PSS.
      SignatureAlgorithms = RSA+SHA256:RSA+SHA384:RSA+SHA512:ECDSA+SHA256:ECDSA+SHA384

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

With both settings applied, the ``ClientHello`` contains only
algorithms that S7 PLCs understand and the handshake completes
normally.

PLC Password Authentication
----------------------------

If the PLC has a password configured (``Full access (no protection)``
disabled in TIA Portal), pass it to the synchronous client's ``connect``
method. The client applies it to either the legacy SessionKey flow or the
TLS legitimation flow, as appropriate for the PLC:

.. code-block:: python

   from s7commplus import Client

   client = Client()
   client.connect(
       "192.168.1.10",
       use_tls=True,
       password="hunter2",
   )
   data = client.db_read(1, 0, 4)

For an older V1 PLC, omit ``use_tls=True``; the password is then used by the
post-SessionKey legitimation exchange. The asynchronous client currently
supports password authentication only on TLS connections, using
``await client.authenticate(...)`` after connecting.

The explicit synchronous ``authenticate`` method is also TLS-only. It
auto-detects whether the TLS PLC uses the legacy SHA-1 challenge or the newer
AES-256-CBC challenge. For accounts with a username (TIA Portal V17+
user-based access control), pass it explicitly:

.. code-block:: python

   client.authenticate(password="hunter2", username="operator")

S7-200 / Logo (TSAP Connection)
--------------------------------

S7-200 and Logo PLCs require TSAP addressing via TSAP addressing:

.. code-block:: python

   from s7 import Client

   client = Client()
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

   from s7 import Client

   client = Client()
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
unchanged — ``snap7`` is an alias for ``s7``:

.. code-block:: python

   import snap7

   client = snap7.Client()
   client.connect("192.168.1.10", 0, 1)
