#!/bin/sh

export PYTHONPATH=.
printf "Running test_partner.py ----------------------------------------------\n\n"
sudo nosetests test/test_partner.py
printf "Running test_server.py  ----------------------------------------------\n\n"
nosetests test/test_server.py
printf "Running test_client.py  ----------------------------------------------\n\n"
nosetests test/test_client.py
printf "Running test_client_async.py  ----------------------------------------------\n\n"
nosetests test/test_client_async.py
printf "Running test_util.py    ----------------------------------------------\n\n"
nosetests test/test_util.py

