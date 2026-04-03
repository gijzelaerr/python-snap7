Server
======

The ``s7.Server`` is the recommended server for testing. It wraps both a
legacy S7 server and an S7CommPlus server, so test environments can serve
both protocol stacks simultaneously.

.. code:: python

   from s7 import Server

   server = Server()
   server.start(tcp_port=1102)

For quick testing with the legacy server, you can also use the ``mainloop``
helper:

.. code:: python

   from snap7.server import mainloop

   mainloop(tcp_port=1102)

----

s7.Server
---------

.. automodule:: s7.server
   :members:

snap7.Server (legacy)
---------------------

.. automodule:: snap7.server
   :members:
