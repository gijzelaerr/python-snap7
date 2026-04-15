Optimizer
=========

.. warning::

   The read optimizer is **experimental** and its API may change in future
   versions.

The multi-variable read optimizer merges adjacent or overlapping read requests
and packs them into minimal PDU-sized S7 exchanges. This significantly reduces
the number of round-trips when reading many scattered variables.

The optimizer is used automatically by :meth:`~snap7.client.Client.read_multi_vars`
when two or more dict items are passed. It can be disabled per client:

.. code-block:: python

   client.use_optimizer = False          # disable optimizer
   client.multi_read_max_gap = 10        # merge reads up to 10 bytes apart (default 5)

.. automodule:: snap7.optimizer
   :members:
