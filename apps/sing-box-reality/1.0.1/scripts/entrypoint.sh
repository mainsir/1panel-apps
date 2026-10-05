#!/bin/sh
# Generate configuration on every start so 1Panel parameter changes take effect.
set -eu
umask 077

DATA_DIR="${DATA_DIR:-/data}"
KEYS_FILE="$DATA_DIR/keys.env"
CONFIG_FILE="$DATA_DIR/config.json"
CLIENT_FILE="$DATA_DIR/client.txt"

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

PORT=$(port_number "${PANEL_APP_PORT_TCP:-38443}" PANEL_APP_PORT_TCP)
SNI=$(trim "${REALITY_SNI:-www.nvidia.com}")
PUBLIC_HOST=$(trim "${PUBLIC_HOST:-}")
LINK_NAME="${LINK_NAME:-SingBox-Reality}"
SOCKS5_HOST=$(trim "${SOCKS5_HOST:-}")
SOCKS5_PORT=$(trim "${SOCKS5_PORT:-}")
# Do not trim credentials: whitespace can be part of an upstream password.
SOCKS5_USER="${SOCKS5_USER:-}"
SOCKS5_PASS="${SOCKS5_PASS:-}"

if [ -n "$SOCKS5_HOST" ] || [ -n "$SOCKS5_PORT" ]; then
  [ -n "$SOCKS5_HOST" ] && [ -n "$SOCKS5_PORT" ] ||
    fail "SOCKS5_HOST and SOCKS5_PORT must both be set"
  SOCKS5_PORT=$(port_number "$SOCKS5_PORT" SOCKS5_PORT)
fi
if [ -n "$SOCKS5_USER" ] || [ -n "$SOCKS5_PASS" ]; then
  [ -n "$SOCKS5_HOST" ] || fail "SOCKS5 credentials require a proxy host and port"
  [ -n "$SOCKS5_USER" ] && [ -n "$SOCKS5_PASS" ] ||
    fail "SOCKS5_USER and SOCKS5_PASS must both be set"
fi

mkdir -p "$DATA_DIR"
SB_UUID=''
PRIVATE_KEY=''
PUBLIC_KEY=''
SHORT_ID=''
if [ -f "$KEYS_FILE" ]; then
  # Read persisted values as data, without executing shell statements.
  while IFS='=' read -r key value; do
    case "$key" in
      SB_UUID) SB_UUID="$value" ;;
      PRIVATE_KEY) PRIVATE_KEY="$value" ;;
      PUBLIC_KEY) PUBLIC_KEY="$value" ;;
      SHORT_ID) SHORT_ID="$value" ;;
    esac
  done < "$KEYS_FILE"
fi

if [ -z "$SB_UUID" ]; then
  SB_UUID=$(sing-box generate uuid)
fi
if [ -z "$PRIVATE_KEY" ] || [ -z "$PUBLIC_KEY" ]; then
  KP=$(sing-box generate reality-keypair)
  PRIVATE_KEY=$(printf '%s\n' "$KP" | sed -n 's/^PrivateKey:[[:space:]]*//p')
  PUBLIC_KEY=$(printf '%s\n' "$KP" | sed -n 's/^PublicKey:[[:space:]]*//p')
fi
if [ -z "$SHORT_ID" ]; then
  SHORT_ID=$(sing-box generate rand 4 --hex)
fi
[ -n "$SB_UUID" ] && [ -n "$PRIVATE_KEY" ] && [ -n "$PUBLIC_KEY" ] &&
  [ -n "$SHORT_ID" ] || fail "failed to generate secrets"

cat > "$KEYS_FILE" <<KEYS
SB_UUID=$SB_UUID
PRIVATE_KEY=$PRIVATE_KEY
PUBLIC_KEY=$PUBLIC_KEY
SHORT_ID=$SHORT_ID
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
    "tag": "vless-in",
    "listen": "0.0.0.0",
    "listen_port": $PORT,
    "users": [{"uuid": $(json_string "$SB_UUID"), "flow": "xtls-rprx-vision"}],
    "tls": {
      "enabled": true,
      "server_name": $(json_string "$SNI"),
      "reality": {
        "enabled": true,
        "handshake": {"server": $(json_string "$SNI"), "server_port": 443},
        "private_key": $(json_string "$PRIVATE_KEY"),
        "short_id": [$(json_string "$SHORT_ID")]
      }
    }
  }],
  "outbounds": [$OUTBOUND]
}
CONFIG
chmod 600 "$CONFIG_FILE"
sing-box check -c "$CONFIG_FILE"

PUBLIC_HOST="${PUBLIC_HOST:-<服务器IP>}"
case "$PUBLIC_HOST" in
  \[*\]) LINK_HOST="$PUBLIC_HOST" ;;
  *:*) LINK_HOST="[$PUBLIC_HOST]" ;;
  *) LINK_HOST="$PUBLIC_HOST" ;;
esac
SHARE_LINK="vless://$SB_UUID@$LINK_HOST:$PORT?encryption=none&flow=xtls-rprx-vision&security=reality&sni=$(url_encode "$SNI")&fp=chrome&pbk=$(url_encode "$PUBLIC_KEY")&sid=$(url_encode "$SHORT_ID")&type=tcp#$(url_encode "$LINK_NAME")"

cat > "$CLIENT_FILE" <<CLIENT
========== VLESS Reality ==========
地址:   $PUBLIC_HOST
端口:   $PORT
UUID:   $SB_UUID
Flow:   xtls-rprx-vision
SNI:    $SNI
握手:   $SNI:443
公钥:   $PUBLIC_KEY
sid:    $SHORT_ID
指纹:   chrome

节点链接:
$SHARE_LINK
===================================
CLIENT
chmod 600 "$CLIENT_FILE"
echo "OK port=$PORT sni=$SNI outbound=$OUTBOUND_DESC"
echo "client info: $CLIENT_FILE"
exec sing-box run -c "$CONFIG_FILE"
