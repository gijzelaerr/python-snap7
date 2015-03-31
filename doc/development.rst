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
verifies that the code actually works and makes development much easier.  To run
all tests please run from the source::

    $ ./run_tests.sh

Note that some tests require to run as root, since snap7 needs to bind on a
privileged TCP port.

If the test complain about missing Python modules make sure the source directory
is in your PYTHONPATH environment variable, or the python-snap7 module is
installed.

Credits
-------

python-snap7 is created by Gijs Molenaar and Stephan Preeker.

Special thanks to go to Davide Nardella for creating snap7, Thomas Hergenhahn
for his libnodave and Thomas W for his S7comm wireshark plugin.