#!/bin/bash

cp .github/build_scripts/aarch64-linux-gnu.mk snap7-full-1.4.2/build/unix/
pushd snap7-full-1.4.2/build/unix/
make -f "${INPUT_MAKEFILE}" install
popd
mkdir -p snap7/lib/
cp /usr/lib/libsnap7.so snap7/lib/
${INPUT_PYTHON} -m pip install --upgrade pip wheel build auditwheel patchelf setuptools
${INPUT_PYTHON} -m build . --wheel -C="--build-option=--plat-name=${INPUT_PLATFORM}"

auditwheel repair dist/*.whl --plat ${INPUT_PLATFORM} -w ${INPUT_WHEELDIR} --only-plat
