===========
Development
===========

Github
------

We develop python-snap7 on `github <https://github.com/gijzelaerr/python-snap7>`_.
If you have questions about python-snap7 please raise a question in the
`Q&A discussion sessions <https://github.com/gijzelaerr/python-snap7/discussions/categories/q-a>`_.
If you have a bug or feature request for python-snap7 please raise an issue in the
`issue tracker <https://github.com/gijzelaerr/python-snap7/issues>`_. Even better
is if you have a solution to problem! In that case you can make our live easier
by following these steps:

 * fork our repository on Github
 * Add a tests that will fail because of the problem
 * Fix the problem
 * Run the test suite again
 * Commit to your repository
 * Issue a github pull request.

.. note::

   Please keep pull requests **small and single-purpose**. Each PR should do one
   thing well. Large, sweeping PRs -- especially AI-generated ones -- are hard to
   review and likely to be rejected. If you have a large change in mind, break it
   into multiple focused PRs that can be reviewed and merged independently.

We use `ruff <https://docs.astral.sh/ruff/>`_ for linting and formatting, and
`mypy <https://mypy-lang.org/>`_ with strict mode for type checking.
`Pre-commit <https://pre-commit.com/>`_ hooks are configured to enforce code
quality automatically. We use `uv <https://docs.astral.sh/uv/>`_ as our package
manager.

Test suite
----------

python-snap7 comes with a test suite with close to 100% coverage. This test suite
verifies that the code actually works and makes development much easier. To run
all tests please run from the source::

    $ make test

or directly with pytest::

    $ pytest

Tests are organized with pytest markers so you can run specific subsets::

    $ pytest -m client    # Client functionality tests
    $ pytest -m server    # Server functionality tests
    $ pytest -m util      # Utility function tests
    $ pytest -m logo      # Logo PLC tests
    $ pytest -m partner   # Partner connection tests
    $ pytest -m mainloop  # Main loop tests

If the tests complain about missing Python modules make sure the source directory
is in your ``PYTHONPATH`` environment variable, or the python-snap7 module is
installed.

Tox
---

We also have a whole repertoire of linters and code quality checkers in place,
which you can run with::

    $ make tox

Credits
-------

python-snap7 is created by:

* `Gijs Molenaar <https://github.com/gijzelaerr>`_
* Stephan Preeker (stephan at preeker dot net)


Special thanks to:

* Davide Nardella for creating snap7
* Thomas Hergenhahn for his libnodave
* Thomas W for his S7comm wireshark plugin
* `Fabian Beitler <https://github.com/swamper123>`_
* `Nikteliy <https://github.com/nikteliy>`_
* `Lautaro Nahuel Dapino <https://github.com/lautarodapin>`_
