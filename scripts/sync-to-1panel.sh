#!/bin/bash
# Sync this repo's apps into 1Panel local app store.
# Usage: bash scripts/sync-to-1panel.sh
set -euo pipefail

REPO_URL="${REPO_URL:-https://github.com/mainsir/1panel-apps.git}"
REPO_DIR="${REPO_DIR:-/opt/1panel-apps}"
LOCAL_DIR="${LOCAL_DIR:-/opt/1panel/resource/apps/local}"

if [ ! -d "$REPO_DIR/.git" ]; then
  git clone "$REPO_URL" "$REPO_DIR"
else
  git -C "$REPO_DIR" pull --ff-only
fi

mkdir -p "$LOCAL_DIR"
cp -rf "$REPO_DIR"/apps/* "$LOCAL_DIR"/
echo "[ok] synced apps -> $LOCAL_DIR ($(date -Iseconds))"
