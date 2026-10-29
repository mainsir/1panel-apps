#!/bin/sh
# Generate configuration on every start so 1Panel parameter changes take effect.
# TLS is terminated by the front reverse proxy. sing-box only serves VLESS over WebSocket.
set -eu
umask 077

DATA_DIR="${DATA_DIR:-/data}"
KEYS_FILE="$DATA_DIR/keys.env"
CONFIG_FILE="$DATA_DIR/config.json"
CLIENT_FILE="$DATA_DIR/client.txt"
DEFAULT_WS_PATH='/cdn-cgi/assets/v7kQm2pLx9nR'

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

url_encode() {
  printf '%s' "$1" | od -An -v -tu1 | LC_ALL=C awk '
    { for (i = 1; i <= NF; i++) {
        n = $i + 0
        if ((n >= 48 && n <= 57) || (n >= 65 && n <= 90) ||
            (n >= 97 && n <= 122) || n == 45 || n == 46 || n == 95 || n == 126)
          printf "%c", n
        else printf "%%%02X", n
    } }'
}

has_controls() {
  printf '%s' "$1" | od -An -v -tu1 | LC_ALL=C awk '
    { for (i = 1; i <= NF; i++) if (($i + 0) < 32 || ($i + 0) == 127) found = 1 }
    END { exit found ? 0 : 1 }'
}

valid_uuid() {
  case "$1" in
    [0-9a-fA-F][0-9a-fA-F][0-9a-fA-F][0-9a-fA-F][0-9a-fA-F][0-9a-fA-F][0-9a-fA-F][0-9a-fA-F]-[0-9a-fA-F][0-9a-fA-F][0-9a-fA-F][0-9a-fA-F]-[0-9a-fA-F][0-9a-fA-F][0-9a-fA-F][0-9a-fA-F]-[0-9a-fA-F][0-9a-fA-F][0-9a-fA-F][0-9a-fA-F]-[0-9a-fA-F][0-9a-fA-F][0-9a-fA-F][0-9a-fA-F][0-9a-fA-F][0-9a-fA-F][0-9a-fA-F][0-9a-fA-F][0-9a-fA-F][0-9a-fA-F][0-9a-fA-F][0-9a-fA-F])
      return 0 ;;
    *) return 1 ;;
  esac
}

# An address may be a hostname or an IPv6 literal. A single colon is host:port.
require_host() {
  value=$1
  label=$2
  case "$value" in
    ''|.*|*.|-*|*-|*[!A-Za-z0-9._:-]*) fail "$label must be a domain or IP address" ;;
  esac
  case "$value" in
    *:*)
      case "$value" in
        *[!0-9A-Fa-f:]*) fail "$label must be a domain or IP address" ;;
        *:*:*) ;;
        *) fail "$label must not include a port" ;;
      esac
      ;;
  esac
}

# Compose expands $ in interpolated values. Read text fields from the mounted
# 1Panel .env so a value containing $ is the literal saved by the panel.
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

if load_panel_value PUBLIC_HOST; then PUBLIC_HOST="$_panel"; fi
if load_panel_value WS_PATH; then WS_PATH="$_panel"; fi
if load_panel_value SOCKS5_HOST; then SOCKS5_HOST="$_panel"; fi
if load_panel_value SOCKS5_USER; then SOCKS5_USER="$_panel"; fi
if load_panel_value SOCKS5_PASS; then SOCKS5_PASS="$_panel"; fi

PORT=$(port_number "${PANEL_APP_PORT_TCP:-18443}" PANEL_APP_PORT_TCP)
# Loopback only. The front reverse proxy on this host is the public listener.
LISTEN_HOST=127.0.0.1

PUBLIC_HOST=$(trim "${PUBLIC_HOST:-}")
[ -n "$PUBLIC_HOST" ] || fail "PUBLIC_HOST is required"
case "$PUBLIC_HOST" in
  \[*\]) PUBLIC_HOST=${PUBLIC_HOST#[}; PUBLIC_HOST=${PUBLIC_HOST%]} ;;
esac
require_host "$PUBLIC_HOST" PUBLIC_HOST
case "$PUBLIC_HOST" in
  *:*) LINK_HOST="[$PUBLIC_HOST]" ;;
  *) LINK_HOST=$PUBLIC_HOST ;;
esac

# Reject control characters before trim: trim deletes CR/LF anywhere in the value.
if [ -z "${WS_PATH:-}" ]; then
  WS_PATH=$DEFAULT_WS_PATH
fi
if has_controls "$WS_PATH"; then
  fail "WS_PATH contains control characters"
fi
WS_PATH=$(trim "$WS_PATH")
[ -n "$WS_PATH" ] || WS_PATH=$DEFAULT_WS_PATH
case "$WS_PATH" in
  /*) ;;
  *) WS_PATH="/$WS_PATH" ;;
esac

# Fixed client remark. Not a form field.
LINK_NAME=SingBox-WS

SOCKS5_HOST=$(trim "${SOCKS5_HOST:-}")
SOCKS5_PORT=$(trim "${SOCKS5_PORT:-}")
# Do not trim credentials: whitespace can be part of an upstream password.
SOCKS5_USER="${SOCKS5_USER:-}"
SOCKS5_PASS="${SOCKS5_PASS:-}"

if [ -n "$SOCKS5_HOST" ] || [ -n "$SOCKS5_PORT" ]; then
  [ -n "$SOCKS5_HOST" ] && [ -n "$SOCKS5_PORT" ] ||
    fail "SOCKS5_HOST and SOCKS5_PORT must both be set"
  require_host "$SOCKS5_HOST" SOCKS5_HOST
  SOCKS5_PORT=$(port_number "$SOCKS5_PORT" SOCKS5_PORT)
fi
if [ -n "$SOCKS5_USER" ] || [ -n "$SOCKS5_PASS" ]; then
  [ -n "$SOCKS5_HOST" ] || fail "SOCKS5 credentials require a proxy host and port"
  [ -n "$SOCKS5_USER" ] && [ -n "$SOCKS5_PASS" ] ||
    fail "SOCKS5_USER and SOCKS5_PASS must both be set"
fi

mkdir -p "$DATA_DIR"
SB_UUID=''
if [ -f "$KEYS_FILE" ]; then
  # Read the persisted UUID as data. Do not execute the file.
  while IFS= read -r line || [ -n "$line" ]; do
    case "$line" in
      SB_UUID=*) SB_UUID=${line#SB_UUID=} ;;
    esac
  done < "$KEYS_FILE"
fi
SB_UUID=$(trim "$SB_UUID")
if [ -z "$SB_UUID" ]; then
  SB_UUID=$(trim "$(sing-box generate uuid)")
elif ! valid_uuid "$SB_UUID"; then
  fail "SB_UUID in keys.env is invalid"
fi
valid_uuid "$SB_UUID" || fail "failed to generate UUID"

cat > "$KEYS_FILE" <<KEYS
SB_UUID=$SB_UUID
KEYS
chmod 600 "$KEYS_FILE"

if [ -n "$SOCKS5_HOST" ]; then
  AUTH_FIELDS=''
  if [ -n "$SOCKS5_USER" ]; then
    AUTH_FIELDS=", \"username\": $(json_string "$SOCKS5_USER"), \"password\": $(json_string "$SOCKS5_PASS")"
  fi
  OUTBOUND="{\"type\": \"socks\", \"tag\": \"socks-out\", \"server\": $(json_string "$SOCKS5_HOST"), \"server_port\": $SOCKS5_PORT, \"version\": \"5\"$AUTH_FIELDS}"
  OUTBOUND_DESC="socks5://$SOCKS5_HOST:$SOCKS5_PORT"
else
  OUTBOUND='{"type": "direct", "tag": "direct"}'
  OUTBOUND_DESC=direct
fi

cat > "$CONFIG_FILE" <<CONFIG
{
  "log": {"level": "info", "timestamp": true},
  "inbounds": [{
    "type": "vless",
    "tag": "vless-ws-in",
    "listen": $(json_string "$LISTEN_HOST"),
    "listen_port": $PORT,
    "users": [{"uuid": $(json_string "$SB_UUID")}],
    "transport": {
      "type": "ws",
      "path": $(json_string "$WS_PATH"),
      "max_early_data": 2048,
      "early_data_header_name": $(json_string "Sec-WebSocket-Protocol")
    }
  }],
  "outbounds": [$OUTBOUND]
}
CONFIG
chmod 600 "$CONFIG_FILE"
sing-box check -c "$CONFIG_FILE"

ENC_PATH=$(url_encode "$WS_PATH")
ENC_NAME=$(url_encode "$LINK_NAME")
SHARE_LINK="vless://${SB_UUID}@${LINK_HOST}:443?encryption=none&security=tls&sni=${PUBLIC_HOST}&fp=chrome&type=ws&host=${PUBLIC_HOST}&path=${ENC_PATH}&ed=2048&eh=Sec-WebSocket-Protocol#${ENC_NAME}"

cat > "$CLIENT_FILE" <<CLIENT
========== VLESS + WS + TLS ==========
地址:     $PUBLIC_HOST
端口:     443
UUID:     $SB_UUID
传输:     WebSocket
路径:     $WS_PATH
TLS:      tls (OpenResty / Let's Encrypt)
SNI/Host: $PUBLIC_HOST
指纹:     chrome
本机入站: $LISTEN_HOST:$PORT
出口:     $OUTBOUND_DESC

节点链接:
$SHARE_LINK
======================================
CLIENT
chmod 600 "$CLIENT_FILE"
echo "OK ws ${LISTEN_HOST}:${PORT}${WS_PATH} public=${PUBLIC_HOST}:443 outbound=${OUTBOUND_DESC}"
echo "client info: $CLIENT_FILE"
exec sing-box run -c "$CONFIG_FILE"
