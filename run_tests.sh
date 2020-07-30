#!/usr/bin/env bash

set -v
set -e

export PYTHONPATH=.
sudo venv/bin/nosetests test/test_partner.py
nosetests test/test_server.py
nosetests test/test_client.py
nosetests test/test_client_async.py
nosetests test/test_util.py

