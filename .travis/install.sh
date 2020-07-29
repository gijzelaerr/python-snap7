#!/usr/bin/env bash

set -v
set -e


if [ "$TRAVIS_OS_NAME" = "osx" ]; then
    make setup
fi

if [ "$TRAVIS_OS_NAME" = "linux" ]; then
     docker build . -f .travis/${TARGET}.docker -t python-snap7/${TARGET}
fi


