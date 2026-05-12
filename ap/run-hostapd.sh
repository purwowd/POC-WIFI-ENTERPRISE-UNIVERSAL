#!/usr/bin/env sh
set -eu

SRC_CONF=/etc/hostapd/hostapd.conf
CONF=/tmp/hostapd.conf

cp "$SRC_CONF" "$CONF"

if [ -n "${RADIUS_ADDR:-}" ]; then
  sed -i "s/^auth_server_addr=.*/auth_server_addr=${RADIUS_ADDR}/" "$CONF" || true
  sed -i "s/^acct_server_addr=.*/acct_server_addr=${RADIUS_ADDR}/" "$CONF" || true
fi

if [ -n "${RADIUS_SECRET:-}" ]; then
  sed -i "s/^auth_server_shared_secret=.*/auth_server_shared_secret=${RADIUS_SECRET}/" "$CONF" || true
  sed -i "s/^acct_server_shared_secret=.*/acct_server_shared_secret=${RADIUS_SECRET}/" "$CONF" || true
fi

echo "[ap] starting hostapd with ${CONF}"
exec hostapd -dd "$CONF"

