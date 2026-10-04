#!/bin/bash
set -e
mkdir -p ./data
if [ -f ./scripts/entrypoint.sh ]; then
  chmod +x ./scripts/entrypoint.sh || true
fi
