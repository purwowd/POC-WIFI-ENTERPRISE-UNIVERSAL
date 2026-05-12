#!/usr/bin/env sh
set -eu

SSID="${WIFI_SSID:-LAB-HS20}"
USER="${WIFI_USER:-1510100000000000}"
PASS="${WIFI_PASS:-}"
EAP_METHOD="${EAP_METHOD:-SIM}"   # SIM, AKA, PEAP, or TTLS
PHASE2="${PHASE2:-}"
CA_CERT="${CA_CERT:-/certs/ca.crt}"
LAB_REALM="${LAB_REALM:-wlan.mnc010.mcc510.3gppnetwork.org}"
SIM_PIN="${SIM_PIN:-}"

mkdir -p /evidence

cat > /tmp/wpa.conf <<EOF
ctrl_interface=/run/wpa_supplicant
update_config=0
ap_scan=1
interworking=1
hs20=1
auto_interworking=1

network={
  ssid="${SSID}"
  key_mgmt=WPA-EAP
  eap=${EAP_METHOD}
  identity="${USER}"
EOF

if [ "$EAP_METHOD" = "SIM" ] || [ "$EAP_METHOD" = "AKA" ] || [ "$EAP_METHOD" = "AKA'" ]; then
  cat >> /tmp/wpa.conf <<EOF
  anonymous_identity="anonymous@${LAB_REALM}"
EOF
  if [ -n "$SIM_PIN" ]; then
    cat >> /tmp/wpa.conf <<EOF
  pin="${SIM_PIN}"
EOF
  fi
else
  cat >> /tmp/wpa.conf <<EOF
  password="${PASS}"
  phase2="${PHASE2}"
  ca_cert="${CA_CERT}"
EOF
fi

cat >> /tmp/wpa.conf <<EOF
}
EOF

echo "[victim] NOTE: This victim is a wired container; it validates RADIUS/EAP config only." | tee /evidence/victim_notice.txt
echo "[victim] wpa_supplicant config written to /tmp/wpa.conf" | tee /evidence/victim_status.txt

# We don't have a real WiFi radio in-container. Run wpa_supplicant in config-test mode to avoid touching any real victim device.
echo "[victim] Dry-run parse check for wpa_supplicant config..." | tee -a /evidence/victim_status.txt
wpa_supplicant -t -c /tmp/wpa.conf >/evidence/wpa_parse.log 2>&1 || true

echo "[victim] Done. Inspect /evidence/*.log" | tee -a /evidence/victim_status.txt
sleep infinity

