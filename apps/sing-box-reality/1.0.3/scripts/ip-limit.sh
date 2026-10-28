#!/bin/sh
# Best-effort concurrent source-IP limiter using sing-box Clash API.
# Stock sing-box has no native per-user IP cap; this closes excess connections.
set -eu

CLASH_API="${CLASH_API:-http://127.0.0.1:19090}"
USERS_FILE="${USERS_FILE:-/data/users.json}"
INTERVAL="${IP_LIMIT_INTERVAL:-5}"

http_get() {
  url=$1
  if command -v wget >/dev/null 2>&1; then
    wget -qO- --timeout=3 "$url" 2>/dev/null || true
  elif command -v curl >/dev/null 2>&1; then
    curl -fsS --max-time 3 "$url" 2>/dev/null || true
  else
    return 1
  fi
}

http_delete() {
  url=$1
  if command -v wget >/dev/null 2>&1; then
    wget -qO- --method=DELETE --timeout=3 "$url" >/dev/null 2>&1 || true
  elif command -v curl >/dev/null 2>&1; then
    curl -fsS -X DELETE --max-time 3 "$url" >/dev/null 2>&1 || true
  fi
}

# Wait until Clash API is up
i=0
while [ "$i" -lt 60 ]; do
  body=$(http_get "$CLASH_API/version" || true)
  [ -n "$body" ] && break
  i=$((i + 1))
  sleep 1
done
if [ -z "${body:-}" ]; then
  echo "ip-limit: Clash API not available; max_ips will not be enforced" >&2
  exit 0
fi
echo "ip-limit: watching $CLASH_API using $USERS_FILE"

while true; do
  [ -f "$USERS_FILE" ] || { sleep "$INTERVAL"; continue; }
  conns=$(http_get "$CLASH_API/connections" || true)
  [ -n "$conns" ] || { sleep "$INTERVAL"; continue; }

  # Extract max_ips by user name from users.json into a temp map file: name max_ips
  map="$USERS_FILE.ipmap"
  # shellcheck disable=SC2016
  printf '%s' "$(cat "$USERS_FILE")" | od -An -v -tu1 | LC_ALL=C awk '
    BEGIN { RS=""; }
  ' >/dev/null 2>&1 || true

  # Portable extract: pull "name":"...","uuid":"...","max_ips":N objects
  : > "$map"
  # Split objects roughly
  printf '%s' "$(cat "$USERS_FILE")" | tr '{}' '\n' | while IFS= read -r obj; do
    case "$obj" in
      *\"name\"*)
        name=$(printf '%s' "$obj" | sed -n 's/.*"name":"\([^"]*\)".*/\1/p')
        max=$(printf '%s' "$obj" | sed -n 's/.*"max_ips":\([0-9][0-9]*\).*/\1/p')
        [ -n "$name" ] && [ -n "$max" ] && [ "$max" -gt 0 ] 2>/dev/null &&
          printf '%s %s\n' "$name" "$max" >> "$map"
        ;;
    esac
  done

  [ -s "$map" ] || { sleep "$INTERVAL"; continue; }

  # Dump connections to a work file: id user srcip
  work=$(mktemp 2>/dev/null || echo /tmp/ip-limit-conns.$$)
  : > "$work"
  # Clash API JSON is one blob; extract with sed (best-effort)
  printf '%s' "$conns" | tr '{}' '\n' | while IFS= read -r obj; do
    case "$obj" in
      *\"id\"*)
        id=$(printf '%s' "$obj" | sed -n 's/.*"id":"\([^"]*\)".*/\1/p')
        # Prefer metadata.username / user / inboundUser fields used by clash meta
        user=$(printf '%s' "$obj" | sed -n 's/.*"username":"\([^"]*\)".*/\1/p')
        [ -n "$user" ] || user=$(printf '%s' "$obj" | sed -n 's/.*"user":"\([^"]*\)".*/\1/p')
        src=$(printf '%s' "$obj" | sed -n 's/.*"sourceIP":"\([^"]*\)".*/\1/p')
        [ -n "$id" ] && [ -n "$user" ] && [ -n "$src" ] &&
          printf '%s %s %s\n' "$id" "$user" "$src" >> "$work"
        ;;
    esac
  done

  while IFS=' ' read -r uname maxips; do
    [ -n "$uname" ] || continue
    # Unique IPs currently online for this user
    ips=$(awk -v u="$uname" '$2==u {print $3}' "$work" | sort -u)
    count=$(printf '%s\n' "$ips" | sed '/^$/d' | wc -l | tr -d ' ')
    [ "$count" -gt "$maxips" ] || continue
    # IPs to drop: all beyond the first maxips (stable sort)
    drop_ips=$(printf '%s\n' "$ips" | sed '/^$/d' | awk -v m="$maxips" 'NR>m {print}')
    printf '%s\n' "$drop_ips" | sed '/^$/d' | while IFS= read -r dip; do
      awk -v u="$uname" -v ip="$dip" '$2==u && $3==ip {print $1}' "$work" | while IFS= read -r cid; do
        echo "ip-limit: closing user=$uname ip=$dip id=$cid (max_ips=$maxips)"
        http_delete "$CLASH_API/connections/$cid"
      done
    done
  done < "$map"

  rm -f "$work" "$map"
  sleep "$INTERVAL"
done
