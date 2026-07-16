Server
======

python-snap7 provides two server implementations:

- ``s7commplus.Server``: S7CommPlus server emulator
- ``s7.server.Server``: Legacy S7 server for testing

.. code:: python

   from s7commplus import Server

   server = Server()
   server.start(tcp_port=1102)

For quick testing with the legacy server, you can also use the ``mainloop``
helper:

.. code:: python

   from s7.server import mainloop

   mainloop(tcp_port=1102)

----

s7commplus.Server
-----------------

.. automodule:: s7commplus.server
   :members:

snap7.Server (legacy)
---------------------

.. automodule:: snap7.server
   :members:
