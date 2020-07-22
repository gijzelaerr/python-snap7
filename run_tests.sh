#!/bin/sh

export PYTHONPATH=.
echo -e "Running test_partner.py ----------------------------------------------\n\n"
sudo nosetests test/test_partner.py
echo -e "Running test_server.py  ----------------------------------------------\n\n"
nosetests test/test_server.py
echo -e "Running test_client.py  ----------------------------------------------\n\n"
nosetests test/test_client.py
echo -e "Running test_client_async.py  ----------------------------------------------\n\n"
nosetests test/test_client_async.py
echo -e "Running test_util.py    ----------------------------------------------\n\n"
nosetests test/test_util.py

