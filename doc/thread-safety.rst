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

The heartbeat thread
--------------------

``Client(heartbeat_interval=10)`` starts a daemon thread named
``s7-heartbeat`` when the client connects. Every interval it reads the CPU
state to check that the PLC still answers, and ``client.is_alive`` reports the
result of the last probe. ``disconnect()`` stops the thread. With the default
``heartbeat_interval=0`` no thread is started.

The client holds an internal lock around each request and its reply, so a
probe never lands in the middle of one of your requests. This lock exists for
the heartbeat. It covers a single exchange, not a whole operation: a large
read, an upload or a download takes several exchanges. It does not make a
shared ``Client`` safe to call from several threads, so the two options above
still apply.

Two things follow from the probe running on its own thread:

* With ``auto_reconnect=True`` the heartbeat thread reconnects when a probe
  fails, so the ``on_disconnect`` and ``on_reconnect`` callbacks can run on
  the heartbeat thread. Keep them short and do not touch state that your main
  thread uses without a lock of your own.
* A probe is a request like any other. It counts against
  ``max_requests_per_second``, and your next call waits while one is in
  flight.

``AsyncClient`` has no heartbeat thread. See :doc:`API/async-client`.

Parallel requests on one connection: ``max_parallel``
-----------------------------------------------------

``max_parallel`` is not a thread count. When ``read_multi_vars`` or
``read_tags`` needs more than one PDU, the client sends up to
``client.max_parallel`` requests on its single connection before it reads the
replies, and matches each reply to its request by sequence number. All of this
happens in the calling thread.

``connect()`` sets the value from the negotiated PDU size:

==================  ================
PDU size (bytes)    ``max_parallel``
==================  ================
960 or more         8
480 to 959          4
240 to 479          2
below 240           1
==================  ================

A PLC accepts only a limited number of requests in flight. If multi-variable
reads time out or the PLC drops the connection, send them one at a time:

.. code-block:: python

   client.connect("192.168.1.10", 0, 1)
   client.max_parallel = 1

Set it after ``connect()``, because connecting (but not an automatic
reconnect) sets it again. The value is left alone when
``client.use_optimizer`` is ``False``, and it only affects multi-variable
reads; every other operation sends one request and waits for its reply.
