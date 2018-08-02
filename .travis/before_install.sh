#!/bin/bash

set -x

if [ "$TRAVIS_OS_NAME" = "osx" ]; then
    brew install snap7
    pip install nose mock coverage
    pip3 install nose mock coverage
fi

if [ "$TRAVIS_OS_NAME" = "linux" ]; then
	sudo apt-get update -qq
	sudo apt-get install -y software-properties-common
	sudo add-apt-repository -y ppa:gijzelaar/snap7
	sudo apt-get update -qq
	sudo apt-get install -y libsnap7-dev libsnap71
fi

pip${PYENV} install -r test/requirements.txt
