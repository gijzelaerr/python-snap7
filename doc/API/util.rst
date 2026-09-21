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

DB layout helpers
-----------------

``DB`` and ``Row`` map a textual DB layout specification onto a byte buffer.
They are also exported directly from ``s7`` and ``snap7``.

.. automodule:: snap7.util.db
   :members:
