#!/bin/bash

set -x

if [ "$TRAVIS_OS_NAME" = "osx" ]; then
    brew install snap7
    pip3 install nose mock coverage aiounittest
    python3 -c 'import sys;print(sys.path);print("hello");help("modules");'

    sudo python3 -c 'print("SUUUUUUUUUUUUUUUUUUDDDDDOOOOOOOOOOOOOO");import sys;print(sys.path);print("hello");help("modules");'
fi

if [ "$TRAVIS_OS_NAME" = "linux" ]; then
	sudo apt-get update -qq
	sudo apt-get install -y software-properties-common
	sudo add-apt-repository -y ppa:gijzelaar/snap7
	sudo apt-get update -qq
	sudo apt-get install -y libsnap7-dev libsnap71
fi

pip${PYENV} install -r test/requirements.txt
