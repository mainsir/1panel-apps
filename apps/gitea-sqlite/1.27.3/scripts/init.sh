#!/bin/bash
# Gitea container runs as user git (UID 1000, GID 1000). Ensure host-mounted data directory is writable.
set -e
mkdir -p ./data
chown -R 1000:1000 ./data
