#!/bin/bash
# Run make commands in Docker container

set -euo pipefail

DEBUG="${DEBUG:-}"

[ -n "$DEBUG" ] && set -x

DIR=$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )

docker_args=("-i")
if [ -t 0 ] ; then
# Running in pty terminal
docker_args+=("-t")
fi

exec docker run \
    "${docker_args[@]}" \
    --rm \
    -v "$DIR:$DIR" \
    -w "$DIR" \
    --entrypoint make \
    python:3 \
    "$@"