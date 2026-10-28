#!/bin/sh
# Generate configuration on every start so 1Panel parameter changes take effect.
# TLS is terminated by the front reverse proxy. sing-box only serves VLESS over WebSocket.
# Multi-user: USERS lines are name|uuid-or-empty|max_ips (newline or ; separated).
# Empty USERS keeps single-user mode with the persisted keys.env UUID.
set -eu
umask 077

DATA_DIR="${DATA_DIR:-/data}"
KEYS_FILE="$DATA_DIR/keys.env"
USERS_FILE="$DATA_DIR/users.json"
CONFIG_FILE="$DATA_DIR/config.json"
CLIENT_FILE="$DATA_DIR/client.txt"
DEFAULT_WS_PATH='/cdn-cgi/assets/v7kQm2pLx9nR'
CLASH_API_HOST=127.0.0.1
CLASH_API_PORT=19090

fail() {
  echo "ERROR: $*" >&2
  exit 1
}

trim() {
  printf '%s' "$1" | tr -d '\r' | sed 's/^[[:space:]]*//;s/[[:space:]]*$//'
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

nonneg_int() {
  value=$(trim "$1")
  case "$value" in
    '') printf '0'; return 0 ;;
    *[!0-9]*) fail "$2 must be a non-negative integer" ;;
  esac
  value=$(printf '%s' "$value" | sed 's/^0*//')
  [ -n "$value" ] || value=0
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

lookup_persisted_uuid() {
  _found_uuid=''
  [ -f "$USERS_FILE" ] || return 1
  # users.json is compact: {"name":"...","uuid":"...","max_ips":N}
  _needle=$(printf '"name":"%s"' "$1")
  _obj=$(tr '{' '
' < "$USERS_FILE" | grep -F "$_needle" | head -n1 || true)
  [ -n "$_obj" ] || return 1
  _found_uuid=${_obj#*\"uuid\":\"}
  _found_uuid=${_found_uuid%%\"*}
  [ -n "$_found_uuid" ] || return 1
  valid_uuid "$_found_uuid" || return 1
  return 0
}

if load_panel_value LISTEN_HOST; then LISTEN_HOST="$_panel"; fi
if load_panel_value PUBLIC_HOST; then PUBLIC_HOST="$_panel"; fi
if load_panel_value WS_PATH; then WS_PATH="$_panel"; fi
if load_panel_value LINK_NAME; then LINK_NAME="$_panel"; fi
if load_panel_value USERS; then USERS="$_panel"; fi
if load_panel_value SOCKS5_HOST; then SOCKS5_HOST="$_panel"; fi
if load_panel_value SOCKS5_USER; then SOCKS5_USER="$_panel"; fi
if load_panel_value SOCKS5_PASS; then SOCKS5_PASS="$_panel"; fi

PORT=$(port_number "${PANEL_APP_PORT_TCP:-18443}" PANEL_APP_PORT_TCP)
LISTEN_HOST=$(trim "${LISTEN_HOST:-127.0.0.1}")
[ -n "$LISTEN_HOST" ] || LISTEN_HOST=127.0.0.1
case "$LISTEN_HOST" in
  \[*\]) LISTEN_HOST=${LISTEN_HOST#[}; LISTEN_HOST=${LISTEN_HOST%]} ;;
esac
require_host "$LISTEN_HOST" LISTEN_HOST

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

if [ -z "${LINK_NAME:-}" ]; then
  LINK_NAME=SingBox-WS
fi
if has_controls "$LINK_NAME"; then
  fail "LINK_NAME contains control characters"
fi
LINK_NAME=$(trim "$LINK_NAME")
[ -n "$LINK_NAME" ] || LINK_NAME=SingBox-WS

SOCKS5_HOST=$(trim "${SOCKS5_HOST:-}")
SOCKS5_PORT=$(trim "${SOCKS5_PORT:-}")
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

# Load legacy single UUID
SB_UUID=''
if [ -f "$KEYS_FILE" ]; then
  while IFS= read -r line || [ -n "$line" ]; do
    case "$line" in
      SB_UUID=*) SB_UUID=${line#SB_UUID=} ;;
    esac
  done < "$KEYS_FILE"
fi
SB_UUID=$(trim "$SB_UUID")

# Normalize USERS: allow ; as line separators for single-line 1Panel text fields.
USERS_RAW="${USERS:-}"
USERS_NORM=$(printf '%s' "$USERS_RAW" | tr ';' '\n')

USER_NAMES=''
USER_UUIDS=''
USER_MAX_IPS=''
USER_COUNT=0
NEED_IP_LIMIT=0

append_user() {
  name=$1
  uuid=$2
  max_ips=$3
  USER_COUNT=$((USER_COUNT + 1))
  USER_NAMES="$USER_NAMES
$name"
  USER_UUIDS="$USER_UUIDS
$uuid"
  USER_MAX_IPS="$USER_MAX_IPS
$max_ips"
  if [ "$max_ips" -gt 0 ]; then NEED_IP_LIMIT=1; fi
}

if [ -n "$(printf '%s' "$USERS_NORM" | sed '/^[[:space:]]*$/d')" ]; then
  # Multi-user mode
  # Process via temp file so append_user can update shell vars
  USERS_TMP="$DATA_DIR/.users.parse"
  printf '%s\n' "$USERS_NORM" > "$USERS_TMP"
  SEEN_NAMES="$DATA_DIR/.users.seen"
  : > "$SEEN_NAMES"
  while IFS= read -r raw || [ -n "$raw" ]; do
    line=$(printf '%s' "$raw" | tr -d '\r')
    case "$line" in
      ''|\#*) continue ;;
    esac
    # Split on |
    name=$(printf '%s' "$line" | awk -F'|' '{print $1}')
    uuid=$(printf '%s' "$line" | awk -F'|' '{print $2}')
    max_ips=$(printf '%s' "$line" | awk -F'|' '{print $3}')
    name=$(trim "$name")
    uuid=$(trim "$uuid")
    [ -n "$name" ] || fail "USERS entry missing name: $line"
    if has_controls "$name"; then
      fail "USERS name contains control characters"
    fi
    case "$name" in
      *\|*) fail "USERS name must not contain |" ;;
    esac
    if grep -Fxq "$name" "$SEEN_NAMES" 2>/dev/null; then
      fail "duplicate USERS name: $name"
    fi
    printf '%s\n' "$name" >> "$SEEN_NAMES"
    max_ips=$(nonneg_int "$max_ips" "max_ips for $name")
    if [ -n "$uuid" ]; then
      valid_uuid "$uuid" || fail "invalid UUID for user $name"
    else
      if lookup_persisted_uuid "$name"; then
        uuid=$_found_uuid
      else
        uuid=$(trim "$(sing-box generate uuid)")
        valid_uuid "$uuid" || fail "failed to generate UUID for $name"
      fi
    fi
    append_user "$name" "$uuid" "$max_ips"
  done < "$USERS_TMP"
  rm -f "$USERS_TMP" "$SEEN_NAMES"
  [ "$USER_COUNT" -gt 0 ] || fail "USERS was set but no valid users were parsed"
  # First UUID becomes SB_UUID for upgrade compatibility
  SB_UUID=$(printf '%s' "$USER_UUIDS" | sed '/^$/d' | head -n1)
else
  # Single-user backward compatible
  if [ -z "$SB_UUID" ]; then
    SB_UUID=$(trim "$(sing-box generate uuid)")
  elif ! valid_uuid "$SB_UUID"; then
    fail "SB_UUID in keys.env is invalid"
  fi
  valid_uuid "$SB_UUID" || fail "failed to generate UUID"
  append_user "default" "$SB_UUID" "0"
fi

# Persist keys.env (legacy UUID) and users.json
cat > "$KEYS_FILE" <<KEYS
SB_UUID=$SB_UUID
KEYS
chmod 600 "$KEYS_FILE"

{
  printf '%s\n' "$USER_NAMES" | sed '/^$/d' > "$DATA_DIR/.n"
  printf '%s\n' "$USER_UUIDS" | sed '/^$/d' > "$DATA_DIR/.u"
  printf '%s\n' "$USER_MAX_IPS" | sed '/^$/d' > "$DATA_DIR/.m"
  # Rebuild lists from files for JSON (append_user already filled vars)
  : > "$DATA_DIR/.users.json.build"
  idx=0
  while IFS= read -r uname && IFS= read -r uuid <&3 && IFS= read -r mips <&4; do
    idx=$((idx + 1))
    if [ "$idx" -gt 1 ]; then
      printf ',' >> "$DATA_DIR/.users.json.build"
    fi
    printf '{"name":%s,"uuid":%s,"max_ips":%s}' \
      "$(json_string "$uname")" "$(json_string "$uuid")" "$mips" >> "$DATA_DIR/.users.json.build"
  done < "$DATA_DIR/.n" 3< "$DATA_DIR/.u" 4< "$DATA_DIR/.m"
  printf '[' > "$USERS_FILE"
  cat "$DATA_DIR/.users.json.build" >> "$USERS_FILE"
  printf ']\n' >> "$USERS_FILE"
  rm -f "$DATA_DIR/.n" "$DATA_DIR/.u" "$DATA_DIR/.m" "$DATA_DIR/.users.json.build"
}
chmod 600 "$USERS_FILE"

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

# Build users JSON array for inbound
USERS_JSON=''
printf '%s\n' "$USER_NAMES" | sed '/^$/d' > "$DATA_DIR/.n"
printf '%s\n' "$USER_UUIDS" | sed '/^$/d' > "$DATA_DIR/.u"
idx=0
while IFS= read -r uname && IFS= read -r uuid <&3; do
  idx=$((idx + 1))
  [ "$idx" -gt 1 ] && USERS_JSON="$USERS_JSON, "
  USERS_JSON="$USERS_JSON{\"name\": $(json_string "$uname"), \"uuid\": $(json_string "$uuid")}"
done < "$DATA_DIR/.n" 3< "$DATA_DIR/.u"
rm -f "$DATA_DIR/.n" "$DATA_DIR/.u"

EXPERIMENTAL=''
if [ "$NEED_IP_LIMIT" -eq 1 ]; then
  EXPERIMENTAL=", \"experimental\": {\"clash_api\": {\"external_controller\": $(json_string "${CLASH_API_HOST}:${CLASH_API_PORT}")}}"
fi

cat > "$CONFIG_FILE" <<CONFIG
{
  "log": {"level": "info", "timestamp": true},
  "inbounds": [{
    "type": "vless",
    "tag": "vless-ws-in",
    "listen": $(json_string "$LISTEN_HOST"),
    "listen_port": $PORT,
    "users": [$USERS_JSON],
    "transport": {
      "type": "ws",
      "path": $(json_string "$WS_PATH"),
      "max_early_data": 2048,
      "early_data_header_name": $(json_string "Sec-WebSocket-Protocol")
    }
  }],
  "outbounds": [$OUTBOUND]$EXPERIMENTAL
}
CONFIG
chmod 600 "$CONFIG_FILE"
sing-box check -c "$CONFIG_FILE"

ENC_PATH=$(url_encode "$WS_PATH")

{
  echo "========== VLESS + WS + TLS =========="
  echo "地址:     $PUBLIC_HOST"
  echo "端口:     443"
  echo "传输:     WebSocket"
  echo "路径:     $WS_PATH"
  echo "TLS:      tls (OpenResty / Let's Encrypt)"
  echo "SNI/Host: $PUBLIC_HOST"
  echo "指纹:     chrome"
  echo "本机入站: $LISTEN_HOST:$PORT"
  echo "出口:     $OUTBOUND_DESC"
  echo "用户数:   $USER_COUNT"
  echo ""
  echo "节点链接:"
  printf '%s\n' "$USER_NAMES" | sed '/^$/d' > "$DATA_DIR/.n"
  printf '%s\n' "$USER_UUIDS" | sed '/^$/d' > "$DATA_DIR/.u"
  printf '%s\n' "$USER_MAX_IPS" | sed '/^$/d' > "$DATA_DIR/.m"
  while IFS= read -r uname && IFS= read -r uuid <&3 && IFS= read -r mips <&4; do
    if [ "$uname" = "default" ] && [ "$USER_COUNT" -eq 1 ]; then
      frag=$LINK_NAME
    else
      frag="${LINK_NAME}-${uname}"
    fi
    ENC_NAME=$(url_encode "$frag")
    SHARE_LINK="vless://${uuid}@${LINK_HOST}:443?encryption=none&security=tls&sni=${PUBLIC_HOST}&fp=chrome&type=ws&host=${PUBLIC_HOST}&path=${ENC_PATH}&ed=2048&eh=Sec-WebSocket-Protocol#${ENC_NAME}"
    echo "# $uname  uuid=$uuid  max_ips=$mips"
    echo "$SHARE_LINK"
    echo ""
  done < "$DATA_DIR/.n" 3< "$DATA_DIR/.u" 4< "$DATA_DIR/.m"
  rm -f "$DATA_DIR/.n" "$DATA_DIR/.u" "$DATA_DIR/.m"
  echo "max_ips: 0=unlimited. Enforcement is best-effort via Clash API when max_ips>0."
  echo "======================================"
} > "$CLIENT_FILE"
chmod 600 "$CLIENT_FILE"

echo "OK ws ${LISTEN_HOST}:${PORT}${WS_PATH} public=${PUBLIC_HOST}:443 users=${USER_COUNT} outbound=${OUTBOUND_DESC}"
echo "client info: $CLIENT_FILE"

if [ "$NEED_IP_LIMIT" -eq 1 ] && [ -f /ip-limit.sh ]; then
  CLASH_API="http://${CLASH_API_HOST}:${CLASH_API_PORT}" USERS_FILE="$USERS_FILE" \
    /bin/sh /ip-limit.sh &
fi

exec sing-box run -c "$CONFIG_FILE"
