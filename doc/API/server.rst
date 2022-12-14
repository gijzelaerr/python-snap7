Server
======

If you just need a quick server with some default values initalised, this package provides a default implementation.
To use it you first need to install some aditional dependencies, using:

.. code:: bash

   pip install python-snap7[cli]

Now you can start it using one of the following commands:

.. code:: bash

   python -m snap7.server
   # or, if your Python `Scripts/` folder is on PATH:
   snap7-server

You can optionally provide the port to be used as an argument, like this:

.. code:: bash

   python -m snap7.server --port 102

----

.. automodule:: snap7.server
   :members:

----

.. automodule:: snap7.server.__main__

   .. autofunction:: main(port, dll)
