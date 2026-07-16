Thread Safety
=============

The ``Client`` class is **not** thread-safe. Concurrent calls from multiple
threads on the same ``Client`` instance will corrupt the TCP connection state
and cause unpredictable errors.

**Option 1: One client per thread**

.. code-block:: python

   import threading
   from s7 import Client

   def worker(address: str, rack: int, slot: int) -> None:
       client = Client()
       client.connect(address, rack, slot)
       data = client.db_read(1, 0, 10)
       client.disconnect()

   t1 = threading.Thread(target=worker, args=("192.168.1.10", 0, 1))
   t2 = threading.Thread(target=worker, args=("192.168.1.10", 0, 1))
   t1.start()
   t2.start()

**Option 2: Shared client with a lock**

.. code-block:: python

   import threading
   from s7 import Client

   client = Client()
   client.connect("192.168.1.10", 0, 1)
   lock = threading.Lock()

   def safe_read(db: int, start: int, size: int) -> bytearray:
       with lock:
           return client.db_read(db, start, size)
