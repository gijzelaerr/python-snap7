Util
====

Data type conversion helpers for reading and writing S7 data types (BOOL, INT,
REAL, STRING, etc.):

.. code-block:: python

   from s7 import util

   data = client.db_read(1, 0, 4)
   value = util.get_real(data, 0)

.. automodule:: snap7.util
   :members:
