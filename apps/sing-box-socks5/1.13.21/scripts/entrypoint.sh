#!/bin/sh
# Generate configuration on every start so 1Panel parameter changes take effect.
set -eu
umask 077

DATA_DIR="${DATA_DIR:-/data}"
CONFIG_FILE="$DATA_DIR/config.json"

fail() {
  echo "ERROR: $*" >&2
  exit 1
}

trim() {
  printf '%s' "$1" | tr -d '\r\n' | sed 's/^[[:space:]]*//;s/[[:space:]]*$//'
}

port_number() {
  value=$(trim "$1")
  case "$value" in
    ''|*[!0-9]*) fail "$2 must be an integer from 1 to 65535" ;;
  esac
  value=$(printf '%s' "$value" | sed 's/^0*//')
  [ -n "$value" ] && [ "${#value}" -le 5 ] && [ "$value" -le 65535 ] ||
    fail "$2 must be an integer from 1 to 65535"
  printf '%s' "$value"
}

# Byte-based encoding preserves UTF-8 and trailing newlines without extra packages.
json_string() {
  printf '%s' "$1" | od -An -v -tu1 | LC_ALL=C awk '
    BEGIN { printf "\"" }
    { for (i = 1; i <= NF; i++) {
        n = $i + 0
        if (n == 34 || n == 92) printf "\\%c", n
        else if (n < 32) printf "\\u%04x", n
        else printf "%c", n
    } }
    END { printf "\"" }'
}

# Compose expands $ in interpolated values. Read credentials from the mounted
# 1Panel .env so a password containing $ is the literal saved value.
load_panel_value() {
  _panel=''
  file=${PANEL_ENV_FILE:-/run/panel.env}
  [ -f "$file" ] || return 1
  line=$(grep -E "^$1=" "$file" | tail -n 1 | tr -d '\r' || true)
  [ -n "$line" ] || return 1
  _panel=${line#*=}
  case "$_panel" in
    \"*\") _panel=${_panel#\"}; _panel=${_panel%\"} ;;
    \'*\') _panel=${_panel#\'}; _panel=${_panel%\'} ;;
  esac
  return 0
}

if load_panel_value PROXY_USERNAME; then
  PROXY_USERNAME="$_panel"
fi
if load_panel_value PROXY_PASSWORD; then
  PROXY_PASSWORD="$_panel"
fi

PORT=$(port_number "${PANEL_APP_PORT_SOCKS:-10001}" PANEL_APP_PORT_SOCKS)
LOG_LEVEL=$(trim "${LOG_LEVEL:-warn}")
INBOUND_TYPE=$(trim "${INBOUND_TYPE:-socks}")
# Do not trim credentials: whitespace can be part of a password.
PROXY_USERNAME="${PROXY_USERNAME-}"
PROXY_PASSWORD="${PROXY_PASSWORD-}"

case "$LOG_LEVEL" in
  warn|info|error|debug) ;;
  *) fail "LOG_LEVEL must be warn, info, error, or debug" ;;
esac

case "$INBOUND_TYPE" in
  socks) INBOUND_TAG=socks-in ;;
  mixed) INBOUND_TAG=mixed-in ;;
  *) fail "INBOUND_TYPE must be socks or mixed" ;;
esac

[ -n "$PROXY_USERNAME" ] && [ -n "$PROXY_PASSWORD" ] ||
  fail "PROXY_USERNAME and PROXY_PASSWORD are required"

mkdir -p "$DATA_DIR"
USER_JSON=$(json_string "$PROXY_USERNAME")
PASS_JSON=$(json_string "$PROXY_PASSWORD")

cat > "$CONFIG_FILE" <<CONFIG
{
  "log": {"level": "$LOG_LEVEL", "timestamp": true},
  "inbounds": [{
    "type": "$INBOUND_TYPE",
    "tag": "$INBOUND_TAG",
    "listen": "0.0.0.0",
    "listen_port": $PORT,
    "users": [{"username": $USER_JSON, "password": $PASS_JSON}]
  }],
  "outbounds": [{"type": "direct", "tag": "direct"}]
}
CONFIG
chmod 600 "$CONFIG_FILE"
sing-box check -c "$CONFIG_FILE"
echo "OK inbound=$INBOUND_TYPE port=$PORT log=$LOG_LEVEL"
exec sing-box run -c "$CONFIG_FILE"
