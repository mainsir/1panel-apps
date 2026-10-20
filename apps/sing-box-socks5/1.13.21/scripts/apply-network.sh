#!/bin/bash
# Apply NETWORK_MODE from ./.env before the container starts.
# 1Panel runs init.sh on install and upgrade.sh on upgrade, after the package
# compose file is in the install directory. Editing parameters does not re-run
# these hooks, so the network mode cannot be changed from the parameter form.
set -euo pipefail

if [ ! -f ./.env ]; then
  echo "ERROR: ./.env not found; run from the 1Panel install directory" >&2
  exit 1
fi

mode=$(grep -E '^NETWORK_MODE=' ./.env | tail -n1 | cut -d= -f2- | tr -d '\r' || true)
mode="${mode#"${mode%%[![:space:]]*}"}"
mode="${mode%"${mode##*[![:space:]]}"}"
mode="${mode#\"}"
mode="${mode%\"}"
mode="${mode#\'}"
mode="${mode%\'}"

case "$mode" in
  host)
    cp ./scripts/docker-compose.host.yml ./docker-compose.yml
    echo "OK network=host"
    ;;
  bridge|"")
    echo "OK network=bridge"
    ;;
  *)
    echo "ERROR: NETWORK_MODE must be bridge or host, got: ${mode}" >&2
    exit 1
    ;;
esac
