#!/bin/bash

set -e
set -x

if [ "$TRAVIS_OS_NAME" = "osx" ]; then
	brew install snap7 python python3
fi

if [ "$TRAVIS_OS_NAME" = "linux" ]; then
	sudo apt-get update -qq
	sudo apt-get install -y software-properties-common
	sudo add-apt-repository -y ppa:gijzelaar/snap7
	sudo apt-get update -qq
	sudo apt-get install -y libsnap7-dev libsnap71
fi

pip install -r test/requirements.txt
