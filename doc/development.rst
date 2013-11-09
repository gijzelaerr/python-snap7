development
===========

Github
------

We develop python-snap7 on `github <https://github.com/gijzelaerr/python-snap7>`_.
If you have any problems with python-snap7 please raise an issue in the
`issue tracker <https://github.com/gijzelaerr/python-snap7/issues>`_. Even better
is if you have a solution to problem! In that case you can make our live easier
by following these steps:

 * fork our repository on github
 * Add a tests that will fail because of the problem
 * Fix the problem
 * Run the test suite again
 * Commit to your repository
 * Issue a github pullrequest.

Also we try to be as much pep8 compatible as possible, where possible and
reasonable.

Test suite
----------

python-snap7 comes with a test suite with 100% coverage. This test suite
verifies that the code actually works and makes development much easier. For now
the client tests require a running fake server. Due to the design of the snap7
library the server needs to run on TCP port 102. On unix all ports in the range
from 0 to 1023 need to as root, so also this process needs to as root. Also the
server tests need to run as root. To run all tests please run::

    $ sudo python test/test_partner.py
    $ sudo python test/test_server.py
    $ nohup sudo snap7/bin/snap7-server.py &  # this runs a snap7 in the background
    $ python test/test_client.py              # the client tests don't need to run as root

If the test complain about missing Python modules make sure the source directory
is in your PYTHONPATH environment variable, or the python-snap7 module is
installed.
