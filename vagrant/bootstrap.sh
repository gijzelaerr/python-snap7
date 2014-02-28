#!/bin/sh

# install software from ubuntu repositories
sudo apt-get update
sudo apt-get install -y software-properties-common python-software-properties python-nose

# add the snap7 launchpad PPA
sudo add-apt-repository ppa:gijzelaar/snap7
sudo apt-get update

# install snap7
sudo apt-get install libsnap7-dev libsnap71
sudo ldconfig

# install python-snap7
cd /vagrant
sudo python ./setup.py install
