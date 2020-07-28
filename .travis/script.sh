#!/usr/bin/env bash

set -v
set -e

if [ "$TRAVIS_OS_NAME" = "osx" ]; then
  make test
fi

if [ "$TRAVIS_OS_NAME" = "linux" ]; then
    docker run python-snap7/${TARGET} make test
fi
