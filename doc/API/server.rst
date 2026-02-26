Server
======

The pure Python server implementation provides a simulated S7 server for testing.

To start a server programmatically:

.. code:: python

   from snap7.server import Server, mainloop

   # Quick start with mainloop helper
   mainloop(tcp_port=1102)

   # Or create and configure manually
   server = Server()
   server.start(port=1102)

----

.. automodule:: snap7.server
   :members:
