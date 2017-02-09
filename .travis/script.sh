#!/bin/bash

set -x

if [ "$TRAVIS_OS_NAME" = "linux" ]; then
    NOSETESTS=${VIRTUAL_ENV}/bin/nosetests
else
    NOSETESTS=/usr/local/bin/nosetests
fi

sudo ${NOSETESTS} --with-coverage test/test_partner.py
nosetests --with-coverage test/test_server.py
nosetests --with-coverage test/test_client.py
nosetests --with-coverage test/test_util.py
