#!/bin/bash
# Fetch one repository snapshot and mirror each app package into the local store.
set -euo pipefail

REPO_URL="${REPO_URL:-https://github.com/mainsir/1panel-apps.git}"
LOCAL_DIR="${LOCAL_DIR:-/opt/1panel/resource/apps/local}"

for cmd in git rsync flock; do
  command -v "$cmd" >/dev/null || { echo "ERROR: $cmd is required" >&2; exit 1; }
done

TMP_DIR=$(mktemp -d /tmp/1panel-apps-sync-XXXXXX)
trap 'rm -rf "$TMP_DIR"' EXIT
trap 'exit 1' HUP INT TERM

echo "Fetching application packages: $REPO_URL"
git clone -q --depth 1 -- "$REPO_URL" "$TMP_DIR/repo"
SOURCE="$TMP_DIR/repo/apps"
[ -d "$SOURCE" ] && [ ! -L "$SOURCE" ] || { echo "ERROR: apps directory is missing or invalid" >&2; exit 1; }
shopt -s nullglob
apps=("$SOURCE"/*)
[ "${#apps[@]}" -gt 0 ] || { echo "ERROR: no application packages found" >&2; exit 1; }

# Check the complete source before modifying any packages in the destination.
for app in "${apps[@]}"; do
  key="${app##*/}"
  [[ "$key" =~ ^[a-z0-9][a-z0-9-]*$ ]] && [ -d "$app" ] && [ ! -L "$app" ] &&
    [ -f "$app/data.yml" ] && [ -f "$app/README.md" ] || {
      echo "ERROR: invalid application package: $key" >&2; exit 1;
    }
  if [ -L "$LOCAL_DIR/$key" ] || { [ -e "$LOCAL_DIR/$key" ] && [ ! -d "$LOCAL_DIR/$key" ]; }; then
    echo "ERROR: destination is not a regular directory: $LOCAL_DIR/$key" >&2
    exit 1
  fi
done

mkdir -p "$LOCAL_DIR"
exec 9>"$LOCAL_DIR/.1panel-apps-sync.lock"
flock -n 9 || { echo "ERROR: another synchronization is running" >&2; exit 1; }
for app in "${apps[@]}"; do
  key="${app##*/}"
  echo "Syncing: $key"
  # Deletions are scoped to this app key. Other local apps remain untouched.
  rsync -a --delete-delay --delay-updates -- "$app/" "$LOCAL_DIR/$key/"
done

echo "Application packages synchronized: $LOCAL_DIR"
