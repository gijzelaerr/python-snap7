#!/bin/sh

export PYTHONPATH=.
echo "Running test_partner.py ----------------------------------------------\n\n"
sudo nosetests test/test_partner.py
echo "Running test_server.py  ----------------------------------------------\n\n"
nosetests test/test_server.py
echo "Running test_client.py  ----------------------------------------------\n\n"
nosetests test/test_client.py
echo "Running test_util.py    ----------------------------------------------\n\n"
nosetests test/test_util.py

