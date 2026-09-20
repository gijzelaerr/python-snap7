Partner
=======

The ``Partner`` class implements S7 peer-to-peer communication for
bidirectional data exchange using BSend/BRecv. Both partners have equal
rights and can send data asynchronously. Partner is part of the legacy
``s7`` package.

.. code:: python

   from s7 import Partner

   partner = Partner(active=True)
   partner.port = 102
   partner.r_id = 0x00000001
   partner.start_to("0.0.0.0", "192.168.1.10", 0x1300, 0x1301)
   partner.set_send_data(b"Hello")
   partner.b_send()
   partner.stop()

----

.. automodule:: snap7.partner
   :members:
