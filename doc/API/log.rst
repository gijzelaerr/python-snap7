Logging
=======

Structured logging with PLC connection context for multi-PLC environments.

The :class:`~snap7.log.PLCLoggerAdapter` automatically injects PLC host,
rack, and slot into every log message:

.. code-block:: python

   import logging
   logging.basicConfig(level=logging.DEBUG)

   from s7 import Client
   client = Client()
   client.connect("192.168.1.10", 0, 1)
   # Logs: [192.168.1.10 R0/S1] Connected to 192.168.1.10:102 ...

For JSON output (ELK, Datadog, Loki):

.. code-block:: python

   from snap7.log import JSONFormatter

   handler = logging.StreamHandler()
   handler.setFormatter(JSONFormatter())
   logging.getLogger("snap7").addHandler(handler)

API reference
-------------

.. automodule:: snap7.log
   :members:
