#!/bin/bash
# kasm-user runs with UID 1000, GID 1000. Ensure host-mounted home/data directory is writable.
set -e
mkdir -p ./data
chown -R 1000:1000 ./data
