#!/bin/bash
# Gitea container runs as user git (UID 1000, GID 1000). Ensure host-mounted data directory is writable.
# Source: https://docs.gitea.com/installation/install-with-docker/
set -e
mkdir -p ./data
chown -R 1000:1000 ./data
