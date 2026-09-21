Rate Limiter
============

The synchronous and asynchronous clients create a limiter from their
``max_requests_per_second`` and ``rate_limit_*`` constructor arguments. Most
applications should configure the client instead of constructing this class
directly.

.. automodule:: snap7.rate_limiter
   :members:
