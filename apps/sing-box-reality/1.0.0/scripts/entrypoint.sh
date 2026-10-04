#!/bin/sh
# Simple VLESS + Reality (sing-box) bootstrap
set -e

DATA_DIR="${DATA_DIR:-/data}"
KEYS_FILE="${DATA_DIR}/keys.env"
CONFIG_FILE="${DATA_DIR}/config.json"
CLIENT_FILE="${DATA_DIR}/client.txt"
SHARE_FILE="${DATA_DIR}/share.link"

PORT="${PANEL_APP_PORT_TCP:-38443}"
SNI="${REALITY_SNI:-www.nvidia.com}"
DEST="${REALITY_DEST:-www.nvidia.com}"
DEST_PORT="${REALITY_DEST_PORT:-443}"
PUBLIC_HOST="${PUBLIC_HOST:-}"
FP="${FINGERPRINT:-chrome}"
LINK_NAME="${LINK_NAME:-SingBox-Reality}"
FORM_UUID="${UUID:-}"

trim() {
  printf '%s' "$1" | tr -d '\r\n' | sed 's/^[[:space:]]*//;s/[[:space:]]*$//'
}

mkdir -p "$DATA_DIR"

if [ -f "$KEYS_FILE" ]; then
  # shellcheck disable=SC1090
  . "$KEYS_FILE"
fi

SB_UUID="$(trim "${SB_UUID:-}")"
PRIVATE_KEY="$(trim "${PRIVATE_KEY:-}")"
PUBLIC_KEY="$(trim "${PUBLIC_KEY:-}")"
SHORT_ID="$(trim "${SHORT_ID:-}")"
FORM_UUID="$(trim "$FORM_UUID")"
SNI="$(trim "$SNI")"
DEST="$(trim "$DEST")"
PUBLIC_HOST="$(trim "$PUBLIC_HOST")"
PORT="$(trim "$PORT")"
DEST_PORT="$(trim "$DEST_PORT")"
FP="$(trim "$FP")"
LINK_NAME="$(trim "$LINK_NAME")"

if [ -z "$SB_UUID" ]; then
  if [ -n "$FORM_UUID" ]; then
    SB_UUID="$FORM_UUID"
  else
    SB_UUID="$(sing-box generate uuid | tr -d '\r\n')"
  fi
fi

if [ -z "$PRIVATE_KEY" ] || [ -z "$PUBLIC_KEY" ]; then
  KP="$(sing-box generate reality-keypair)"
  PRIVATE_KEY="$(printf '%s\n' "$KP" | grep -i private | head -n1 | sed 's/.*:[ \t]*//' | tr -d '\r\n[:space:]')"
  PUBLIC_KEY="$(printf '%s\n' "$KP" | grep -i public | head -n1 | sed 's/.*:[ \t]*//' | tr -d '\r\n[:space:]')"
fi

if [ -z "$SHORT_ID" ]; then
  SHORT_ID="$(sing-box generate rand 4 --hex 2>/dev/null | tr -d '\r\n[:space:]' | tr 'A-F' 'a-f')"
  if [ -z "$SHORT_ID" ]; then
    SHORT_ID="$(sing-box generate uuid | tr -d '-' | cut -c1-8)"
  fi
fi

if [ -z "$PRIVATE_KEY" ] || [ -z "$PUBLIC_KEY" ] || [ -z "$SB_UUID" ] || [ -z "$SHORT_ID" ]; then
  echo "ERROR: failed to generate secrets" >&2
  exit 1
fi

cat > "$KEYS_FILE" <<EOF
SB_UUID=${SB_UUID}
PRIVATE_KEY=${PRIVATE_KEY}
PUBLIC_KEY=${PUBLIC_KEY}
SHORT_ID=${SHORT_ID}
EOF
chmod 600 "$KEYS_FILE" 2>/dev/null || true

# Minimal config — no domain_strategy (deprecated on new sing-box)
cat > "$CONFIG_FILE" <<EOF
{
  "log": {
    "level": "info",
    "timestamp": true
  },
  "inbounds": [
    {
      "type": "vless",
      "tag": "vless-in",
      "listen": "0.0.0.0",
      "listen_port": ${PORT},
      "users": [
        {
          "uuid": "${SB_UUID}",
          "flow": "xtls-rprx-vision"
        }
      ],
      "tls": {
        "enabled": true,
        "server_name": "${SNI}",
        "reality": {
          "enabled": true,
          "handshake": {
            "server": "${DEST}",
            "server_port": ${DEST_PORT}
          },
          "private_key": "${PRIVATE_KEY}",
          "short_id": [
            "${SHORT_ID}"
          ]
        }
      }
    }
  ],
  "outbounds": [
    {
      "type": "direct",
      "tag": "direct"
    }
  ]
}
EOF

if [ -z "$PUBLIC_HOST" ]; then
  PUBLIC_HOST="<服务器IP>"
fi

SAFE_NAME="$(printf '%s' "$LINK_NAME" | sed 's/ /%20/g')"
SHARE_LINK="vless://${SB_UUID}@${PUBLIC_HOST}:${PORT}?encryption=none&flow=xtls-rprx-vision&security=reality&sni=${SNI}&fp=${FP}&pbk=${PUBLIC_KEY}&sid=${SHORT_ID}&type=tcp#${SAFE_NAME}"

cat > "$CLIENT_FILE" <<EOF
========== VLESS Reality ==========
地址:   ${PUBLIC_HOST}
端口:   ${PORT}
UUID:   ${SB_UUID}
Flow:   xtls-rprx-vision
SNI:    ${SNI}
握手:   ${DEST}:${DEST_PORT}
公钥:   ${PUBLIC_KEY}
sid:    ${SHORT_ID}
指纹:   ${FP}

分享链接:
${SHARE_LINK}
===================================
EOF

printf '%s\n' "$SHARE_LINK" > "$SHARE_FILE"
chmod 600 "$CLIENT_FILE" "$SHARE_FILE" 2>/dev/null || true

echo "OK port=${PORT} sni=${SNI} dest=${DEST}"
echo "share: ${SHARE_FILE}"

sing-box check -c "$CONFIG_FILE"
exec sing-box run -c "$CONFIG_FILE"
