#!/bin/bash
# kasm-user runs with UID 1000, GID 1000. Ensure host-mounted home/data directory is writable.
# Source: https://github.com/kasmtech/workspaces-core-images/blob/develop/dockerfile-kasm-core
set -e
mkdir -p ./data
chown -R 1000:1000 ./data
