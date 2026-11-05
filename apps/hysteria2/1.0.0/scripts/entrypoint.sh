#!/bin/sh
# Generate Hysteria2 config on every start so 1Panel form changes take effect.
# Uses host TLS certs + masquerade (proxy or static file) for camouflage.
set -eu
umask 077

DATA_DIR="${DATA_DIR:-/data}"
KEYS_FILE="$DATA_DIR/keys.env"
CONFIG_FILE="$DATA_DIR/config.yaml"
CLIENT_FILE="$DATA_DIR/client.txt"
CERT_MOUNT="${CERT_MOUNT:-/data/certs}"
MASQ_DIR="${MASQ_DIR:-/www/masq}"

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

has_controls() {
  printf '%s' "$1" | od -An -v -tu1 | LC_ALL=C awk '
    { for (i = 1; i <= NF; i++) if (($i + 0) < 32 || ($i + 0) == 127) found = 1 }
    END { exit found ? 0 : 1 }'
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
if load_panel_value CERT_FILE; then CERT_FILE="$_panel"; fi
if load_panel_value KEY_FILE; then KEY_FILE="$_panel"; fi
if load_panel_value MASQUERADE_TYPE; then MASQUERADE_TYPE="$_panel"; fi
if load_panel_value MASQUERADE_URL; then MASQUERADE_URL="$_panel"; fi
if load_panel_value BANDWIDTH_UP; then BANDWIDTH_UP="$_panel"; fi
if load_panel_value BANDWIDTH_DOWN; then BANDWIDTH_DOWN="$_panel"; fi
if load_panel_value IGNORE_CLIENT_BANDWIDTH; then IGNORE_CLIENT_BANDWIDTH="$_panel"; fi
if load_panel_value LINK_NAME; then LINK_NAME="$_panel"; fi

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

CERT_FILE=$(trim "${CERT_FILE:-fullchain.pem}")
KEY_FILE=$(trim "${KEY_FILE:-privkey.pem}")
[ -n "$CERT_FILE" ] || fail "CERT_FILE is required"
[ -n "$KEY_FILE" ] || fail "KEY_FILE is required"
case "$CERT_FILE" in
  */*|*\.\.*) fail "CERT_FILE must be a bare filename" ;;
esac
case "$KEY_FILE" in
  */*|*\.\.*) fail "KEY_FILE must be a bare filename" ;;
esac
CERT_PATH="$CERT_MOUNT/$CERT_FILE"
KEY_PATH="$CERT_MOUNT/$KEY_FILE"
[ -f "$CERT_PATH" ] || fail "certificate not found: $CERT_PATH (mount host CERT_DIR)"
[ -f "$KEY_PATH" ] || fail "private key not found: $KEY_PATH (mount host CERT_DIR)"

MASQUERADE_TYPE=$(trim "${MASQUERADE_TYPE:-proxy}" | tr '[:upper:]' '[:lower:]')
case "$MASQUERADE_TYPE" in
  proxy|file) ;;
  *) fail "MASQUERADE_TYPE must be proxy or file" ;;
esac

MASQUERADE_URL=$(trim "${MASQUERADE_URL:-https://www.microsoft.com}")
[ -n "$MASQUERADE_URL" ] || MASQUERADE_URL=https://www.microsoft.com
case "$MASQUERADE_URL" in
  http://*|https://*) ;;
  *) fail "MASQUERADE_URL must start with http:// or https://" ;;
esac

BANDWIDTH_UP=$(trim "${BANDWIDTH_UP:-}")
BANDWIDTH_DOWN=$(trim "${BANDWIDTH_DOWN:-}")

IGNORE_CLIENT_BANDWIDTH=$(trim "${IGNORE_CLIENT_BANDWIDTH:-true}" | tr '[:upper:]' '[:lower:]')
case "$IGNORE_CLIENT_BANDWIDTH" in
  true|false|1|0|yes|no) ;;
  *) fail "IGNORE_CLIENT_BANDWIDTH must be true or false" ;;
esac
case "$IGNORE_CLIENT_BANDWIDTH" in
  1|yes) IGNORE_CLIENT_BANDWIDTH=true ;;
  0|no) IGNORE_CLIENT_BANDWIDTH=false ;;
esac

if [ -z "${LINK_NAME:-}" ]; then
  LINK_NAME=Hysteria2
fi
if has_controls "$LINK_NAME"; then
  fail "LINK_NAME contains control characters"
fi
LINK_NAME=$(trim "$LINK_NAME")
[ -n "$LINK_NAME" ] || LINK_NAME=Hysteria2

mkdir -p "$DATA_DIR"

# Persist password: form value wins when non-empty; else reuse keys.env; else generate.
FORM_PASSWORD="${PASSWORD:-}"
# Do not trim password: whitespace can be intentional.
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

BW_BLOCK=''
if [ -n "$BANDWIDTH_UP" ] || [ -n "$BANDWIDTH_DOWN" ]; then
  BW_BLOCK='bandwidth:'
  if [ -n "$BANDWIDTH_UP" ]; then
    BW_BLOCK="$BW_BLOCK
  up: $(yaml_string "$BANDWIDTH_UP")"
  fi
  if [ -n "$BANDWIDTH_DOWN" ]; then
    BW_BLOCK="$BW_BLOCK
  down: $(yaml_string "$BANDWIDTH_DOWN")"
  fi
fi

if [ "$MASQUERADE_TYPE" = proxy ]; then
  MASQ_BLOCK="masquerade:
  type: proxy
  proxy:
    url: $(yaml_string "$MASQUERADE_URL")
    rewriteHost: true"
  MASQ_DESC="proxy -> $MASQUERADE_URL"
else
  [ -d "$MASQ_DIR" ] || fail "masquerade file dir missing: $MASQ_DIR"
  MASQ_BLOCK="masquerade:
  type: file
  file:
    dir: $(yaml_string "$MASQ_DIR")"
  MASQ_DESC="file -> $MASQ_DIR"
fi

{
  printf '%s\n' "listen: :$PORT"
  printf '%s\n' "tls:"
  printf '%s\n' "  cert: $(yaml_string "$CERT_PATH")"
  printf '%s\n' "  key: $(yaml_string "$KEY_PATH")"
  printf '%s\n' "auth:"
  printf '%s\n' "  type: password"
  printf '%s\n' "  password: $(yaml_string "$HY2_PASSWORD")"
  if [ -n "$BW_BLOCK" ]; then
    printf '%s\n' "$BW_BLOCK"
  fi
  printf '%s\n' "ignoreClientBandwidth: $IGNORE_CLIENT_BANDWIDTH"
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
忽略客户端带宽: $IGNORE_CLIENT_BANDWIDTH

节点链接:
$SHARE_LINK
================================
CLIENT
chmod 600 "$CLIENT_FILE"

echo "OK hysteria2 udp=:$PORT public=${PUBLIC_HOST} masquerade=${MASQUERADE_TYPE} ignoreClientBandwidth=${IGNORE_CLIENT_BANDWIDTH}"
echo "client info: $CLIENT_FILE"
exec hysteria server -c "$CONFIG_FILE"
