#!/usr/bin/env bash
#
# This should most likely be ran inside the manylinux2014 docker container
#
set -e
set -v

WORKDIR=/tmp/
OUTPUT=dist/

case "$1" in
    3.9)
        VERSION=39
        PLATFORM=""
        ;;
    3.8)
        VERSION=38
        PLATFORM=""
        ;;
    3.7)
        VERSION=37
        PLATFORM="m"
        ;;
    3.6)
        VERSION=36
        PLATFORM="m"
        ;;
    *)
        echo "unsupposed argument"
        exit 1
esac

TARGET=cp${VERSION}-cp${VERSION}${PLATFORM}

/opt/python/${TARGET}/bin/python ./setup.py bdist_wheel -d ${WORKDIR}

auditwheel repair --plat manylinux2014_x86_64 -w ${OUTPUT} ${WORKDIR}/*.whl
