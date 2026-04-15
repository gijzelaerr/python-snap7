Symbolic Addressing
===================

.. warning::

   Symbolic addressing is **experimental** and its API may change in future
   versions.

The :class:`~snap7.util.symbols.SymbolTable` class maps human-readable tag
names to PLC addresses, enabling read/write by name instead of raw byte offsets.

.. code-block:: python

   from s7 import Client, SymbolTable

   symbols = SymbolTable.from_csv("tags.csv")
   client = Client()
   client.connect("192.168.1.10", 0, 1)

   value = symbols.read(client, "Motor1.Speed")
   symbols.write(client, "Motor1.Speed", 1500.0)

CSV format::

   tag_name,db_number,byte_offset,data_type
   Motor1.Speed,1,0,REAL
   Motor1.Running,1,4.0,BOOL
   SetPoint,1,6,INT

Also supports JSON::

   symbols = SymbolTable.from_json("tags.json")

API reference
-------------

.. automodule:: snap7.util.symbols
   :members:
