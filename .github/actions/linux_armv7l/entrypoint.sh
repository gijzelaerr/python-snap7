#!/bin/bash

set -o errexit
set -o pipefail
set -o nounset

exec "$INPUT_SCRIPT"
