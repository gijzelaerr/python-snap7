#!/bin/sh

export PYTHONPATH=.
sudo nosetests test/test_partner.py
sudo nosetests test/test_server.py
sudo PYTHONPATH=. snap7/bin/snap7-server.py &
nosetests test/test_client.py

