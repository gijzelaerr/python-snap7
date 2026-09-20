Server
======

python-snap7 provides a classic S7 server for testing. The ``mainloop`` helper
starts one quickly:

.. code:: python

   from s7.server import mainloop

   mainloop(tcp_port=1102)

----

s7.Server
---------

.. automodule:: snap7.server
   :members:
