#!/bin/sh
# Slim Hysteria2 entrypoint for 1Panel: essentials from form; advanced via YAML.
# Optional SOCKS5 egress (empty = direct). Cert filenames hardcoded to fullchain/privkey.
set -eu
umask 077

DATA_DIR="${DATA_DIR:-/data}"
KEYS_FILE="$DATA_DIR/keys.env"
CONFIG_FILE="$DATA_DIR/config.yaml"
CLIENT_FILE="$DATA_DIR/client.txt"
CERT_MOUNT="${CERT_MOUNT:-/data/certs}"

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

# YAML double-quoted string (UTF-8 safe via byte walk).
yaml_string() {
  printf '%s' "$1" | od -An -v -tu1 | LC_ALL=C awk '
    BEGIN { printf "\"" }
    { for (i = 1; i <= NF; i++) {
        n = $i + 0
        if (n == 34 || n == 92) printf "\\%c", n
        else if (n == 10) printf "\\n"
        else if (n == 13) printf "\\r"
        else if (n == 9) printf "\\t"
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

gen_password() {
  if command -v openssl >/dev/null 2>&1; then
    openssl rand -hex 16
  else
    tr -dc 'A-Za-z0-9' </dev/urandom | head -c 32
  fi
}

# Compose expands $ in interpolated values. Prefer mounted 1Panel .env for literals.
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
if load_panel_value PASSWORD; then PASSWORD="$_panel"; fi
if load_panel_value MASQUERADE_URL; then MASQUERADE_URL="$_panel"; fi
if load_panel_value SOCKS5_HOST; then SOCKS5_HOST="$_panel"; fi
if load_panel_value SOCKS5_PORT; then SOCKS5_PORT="$_panel"; fi
if load_panel_value SOCKS5_USER; then SOCKS5_USER="$_panel"; fi
if load_panel_value SOCKS5_PASS; then SOCKS5_PASS="$_panel"; fi

PORT=$(port_number "${PANEL_APP_PORT_UDP:-443}" PANEL_APP_PORT_UDP)

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

# Hardcoded filenames (1Panel OpenResty / LE defaults). Override via YAML if needed.
CERT_FILE=fullchain.pem
KEY_FILE=privkey.pem
CERT_PATH="$CERT_MOUNT/$CERT_FILE"
KEY_PATH="$CERT_MOUNT/$KEY_FILE"
[ -f "$CERT_PATH" ] || fail "certificate not found: $CERT_PATH (mount host CERT_DIR)"
[ -f "$KEY_PATH" ] || fail "private key not found: $KEY_PATH (mount host CERT_DIR)"

MASQUERADE_URL=$(trim "${MASQUERADE_URL:-https://www.microsoft.com}")
[ -n "$MASQUERADE_URL" ] || MASQUERADE_URL=https://www.microsoft.com
case "$MASQUERADE_URL" in
  http://*|https://*) ;;
  *) fail "MASQUERADE_URL must start with http:// or https://" ;;
esac

SOCKS5_HOST=$(trim "${SOCKS5_HOST:-}")
SOCKS5_PORT_RAW=$(trim "${SOCKS5_PORT:-}")
# Do not trim user/pass: whitespace can be intentional.
SOCKS5_USER="${SOCKS5_USER:-}"
SOCKS5_PASS="${SOCKS5_PASS:-}"

USE_SOCKS=0
if [ -n "$SOCKS5_HOST" ] || [ -n "$SOCKS5_PORT_RAW" ]; then
  [ -n "$SOCKS5_HOST" ] || fail "SOCKS5_HOST required when SOCKS5_PORT is set"
  [ -n "$SOCKS5_PORT_RAW" ] || fail "SOCKS5_PORT required when SOCKS5_HOST is set"
  require_host "$SOCKS5_HOST" SOCKS5_HOST
  SOCKS5_PORT=$(port_number "$SOCKS5_PORT_RAW" SOCKS5_PORT)
  USE_SOCKS=1
fi

LINK_NAME=Hysteria2

mkdir -p "$DATA_DIR"

# Persist password: form value wins when non-empty; else reuse keys.env; else generate.
FORM_PASSWORD="${PASSWORD:-}"
HY2_PASSWORD=''
if [ -f "$KEYS_FILE" ]; then
  while IFS= read -r line || [ -n "$line" ]; do
    case "$line" in
      HY2_PASSWORD=*) HY2_PASSWORD=${line#HY2_PASSWORD=} ;;
    esac
  done < "$KEYS_FILE"
fi

if [ -n "$FORM_PASSWORD" ]; then
  HY2_PASSWORD=$FORM_PASSWORD
elif [ -z "$HY2_PASSWORD" ]; then
  HY2_PASSWORD=$(trim "$(gen_password)")
  [ -n "$HY2_PASSWORD" ] || fail "failed to generate password"
fi
[ -n "$HY2_PASSWORD" ] || fail "PASSWORD is empty"

cat > "$KEYS_FILE" <<KEYS
HY2_PASSWORD=$HY2_PASSWORD
KEYS
chmod 600 "$KEYS_FILE"

MASQ_BLOCK="masquerade:
  type: proxy
  proxy:
    url: $(yaml_string "$MASQUERADE_URL")
    rewriteHost: true"
MASQ_DESC="proxy -> $MASQUERADE_URL"

OUTBOUND_BLOCK=''
EGRESS_DESC=direct
if [ "$USE_SOCKS" -eq 1 ]; then
  case "$SOCKS5_HOST" in
    *:*) SOCKS_ADDR="[$SOCKS5_HOST]:$SOCKS5_PORT" ;;
    *) SOCKS_ADDR="$SOCKS5_HOST:$SOCKS5_PORT" ;;
  esac
  OUTBOUND_BLOCK="outbounds:
  - name: socks
    type: socks5
    socks5:
      addr: $(yaml_string "$SOCKS_ADDR")"
  if [ -n "$SOCKS5_USER" ]; then
    OUTBOUND_BLOCK="$OUTBOUND_BLOCK
      username: $(yaml_string "$SOCKS5_USER")"
  fi
  if [ -n "$SOCKS5_PASS" ]; then
    OUTBOUND_BLOCK="$OUTBOUND_BLOCK
      password: $(yaml_string "$SOCKS5_PASS")"
  fi
  EGRESS_DESC="socks5://$SOCKS_ADDR"
fi

{
  printf '%s\n' "listen: :$PORT"
  printf '%s\n' "tls:"
  printf '%s\n' "  cert: $(yaml_string "$CERT_PATH")"
  printf '%s\n' "  key: $(yaml_string "$KEY_PATH")"
  printf '%s\n' "auth:"
  printf '%s\n' "  type: password"
  printf '%s\n' "  password: $(yaml_string "$HY2_PASSWORD")"
  printf '%s\n' "ignoreClientBandwidth: true"
  if [ -n "$OUTBOUND_BLOCK" ]; then
    printf '%s\n' "$OUTBOUND_BLOCK"
  fi
  printf '%s\n' "$MASQ_BLOCK"
} > "$CONFIG_FILE"
chmod 600 "$CONFIG_FILE"

ENC_PASS=$(url_encode "$HY2_PASSWORD")
ENC_NAME=$(url_encode "$LINK_NAME")
ENC_SNI=$(url_encode "$PUBLIC_HOST")
SHARE_LINK="hysteria2://${ENC_PASS}@${LINK_HOST}:${PORT}/?sni=${ENC_SNI}&insecure=0#${ENC_NAME}"

cat > "$CLIENT_FILE" <<CLIENT
========== Hysteria2 ==========
地址:     $PUBLIC_HOST
端口:     $PORT (UDP)
密码:     $HY2_PASSWORD
SNI:      $PUBLIC_HOST
TLS:      宿主机证书 ($CERT_FILE)
伪装:     $MASQ_DESC
出口:     $EGRESS_DESC

节点链接:
$SHARE_LINK
================================
CLIENT
chmod 600 "$CLIENT_FILE"

echo "OK hysteria2 udp=:$PORT public=${PUBLIC_HOST} masquerade=proxy egress=${EGRESS_DESC}"
echo "client info: $CLIENT_FILE"
exec hysteria server -c "$CONFIG_FILE"
