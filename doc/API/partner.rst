Partner
=======

The ``Partner`` class implements S7 peer-to-peer communication for
bidirectional data exchange using BSend/BRecv. Both partners have equal
rights and can send data asynchronously.

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

s7.Partner
----------

.. automodule:: s7.partner
   :members:

snap7.Partner (legacy)
----------------------

.. automodule:: snap7.partner
   :members:
