#!/bin/sh

export PYTHONPATH=.
sudo nosetests test/test_partner.py
nosetests test/test_server.py
nosetests test/test_client.py
nosetests test/test_util.py

