#!/bin/bash

set -x

if [ "$TRAVIS_OS_NAME" = "linux" ]; then
    NOSETESTS=${VIRTUAL_ENV}/bin/nosetests
else
    NOSETESTS="python${PYENV} -m nose"
fi

PYTHONPATH=.
sudo ${NOSETESTS} --with-coverage test/test_server.py
sudo ${NOSETESTS} --with-coverage test/test_client.py
sudo ${NOSETESTS} --with-coverage test/test_client_async.py
sudo ${NOSETESTS} --with-coverage test/test_util.py
sudo ${NOSETESTS} --with-coverage test/test_partner.py
