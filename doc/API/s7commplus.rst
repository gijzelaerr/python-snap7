S7CommPlus (S7-1200/1500)
=========================

.. warning::

   S7CommPlus support is **experimental**. The API may change in future
   releases. If you encounter problems, please `open an issue
   <https://github.com/gijzelaerr/python-snap7/issues>`_.

The :mod:`snap7.s7commplus` package provides support for Siemens S7-1200 and
S7-1500 PLCs, which use the S7CommPlus protocol instead of the classic S7
protocol used by S7-300/400.

Both synchronous and asynchronous clients are available. When a PLC does not
support S7CommPlus data operations, the clients automatically fall back to the
legacy S7 protocol transparently.

Synchronous client
------------------

.. code-block:: python

   from snap7.s7commplus.client import S7CommPlusClient

   client = S7CommPlusClient()
   client.connect("192.168.1.10")
   data = client.db_read(1, 0, 4)
   client.disconnect()

Asynchronous client
-------------------

.. code-block:: python

   import asyncio
   from snap7.s7commplus.async_client import S7CommPlusAsyncClient

   async def main():
       client = S7CommPlusAsyncClient()
       await client.connect("192.168.1.10")
       data = await client.db_read(1, 0, 4)
       await client.disconnect()

   asyncio.run(main())

V2 connection with TLS
----------------------

S7-1500 PLCs with firmware 2.x use S7CommPlus V2, which requires TLS. Pass
``use_tls=True`` to the ``connect()`` method:

.. code-block:: python

   from snap7.s7commplus.client import S7CommPlusClient

   client = S7CommPlusClient()
   client.connect("192.168.1.10", use_tls=True)
   data = client.db_read(1, 0, 4)
   client.disconnect()

For PLCs with custom certificates, provide the certificate paths:

.. code-block:: python

   client.connect(
       "192.168.1.10",
       use_tls=True,
       tls_cert="/path/to/client.pem",
       tls_key="/path/to/client.key",
       tls_ca="/path/to/ca.pem",
   )

Password authentication
-----------------------

Password-protected PLCs require authentication after connecting. Call
``authenticate()`` before performing data operations:

.. code-block:: python

   from snap7.s7commplus.client import S7CommPlusClient

   client = S7CommPlusClient()
   client.connect("192.168.1.10", use_tls=True)
   client.authenticate(password="my_plc_password")

   data = client.db_read(1, 0, 4)
   client.disconnect()

The method auto-detects whether to use legacy (SHA-1 XOR) or new-style
(AES-256-CBC) authentication based on the PLC firmware version. For new-style
authentication, you can also provide a username:

.. code-block:: python

   client.authenticate(password="my_password", username="admin")

.. note::

   Authentication requires TLS to be active. Calling ``authenticate()``
   without ``use_tls=True`` will raise :class:`~snap7.error.S7ConnectionError`.


Legacy fallback
---------------

If the PLC returns an error for S7CommPlus data operations (common with some
firmware versions), the client automatically falls back to the classic S7
protocol. You can check whether fallback is active:

.. code-block:: python

   client.connect("192.168.1.10")
   if client.using_legacy_fallback:
       print("Using legacy S7 protocol")

API reference
-------------

.. automodule:: snap7.s7commplus.client
   :members:

.. automodule:: snap7.s7commplus.async_client
   :members:

.. automodule:: snap7.s7commplus.connection
   :members:
   :exclude-members: S7CommPlusConnection
