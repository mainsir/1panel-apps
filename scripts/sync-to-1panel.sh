#!/bin/bash
# Sync this repo's apps into 1Panel local app store.
#
# Default: persistent clone + git pull (good for cron).
# One-shot temp clone (always fresh, then cleanup):
#   USE_TMP=1 bash scripts/sync-to-1panel.sh
#
# Usage: bash scripts/sync-to-1panel.sh
set -euo pipefail

REPO_URL="${REPO_URL:-https://github.com/mainsir/1panel-apps.git}"
LOCAL_DIR="${LOCAL_DIR:-/opt/1panel/resource/apps/local}"

if [ "${USE_TMP:-0}" = "1" ]; then
  # Fresh clone into /tmp every run, then remove after copy.
  REPO_DIR="${REPO_DIR:-/tmp/1panel-apps}"
  rm -rf "$REPO_DIR"
  git clone --depth 1 "$REPO_URL" "$REPO_DIR"
  mkdir -p "$LOCAL_DIR"
  cp -rf "$REPO_DIR"/apps/* "$LOCAL_DIR"/
  rm -rf "$REPO_DIR"
else
  # Keep a long-lived checkout and pull updates.
  REPO_DIR="${REPO_DIR:-/opt/1panel-apps}"
  if [ ! -d "$REPO_DIR/.git" ]; then
    git clone "$REPO_URL" "$REPO_DIR"
  else
    git -C "$REPO_DIR" pull --ff-only
  fi
  mkdir -p "$LOCAL_DIR"
  cp -rf "$REPO_DIR"/apps/* "$LOCAL_DIR"/
fi

echo "[ok] synced apps -> $LOCAL_DIR ($(date -Iseconds))"
echo "[note] cp only adds/overwrites apps present in the repo; remove obsolete local apps manually if needed."
