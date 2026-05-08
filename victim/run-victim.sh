#!/usr/bin/env sh
set -eu

SSID="${WIFI_SSID:-LAB-ENTERPRISE}"
USER="${WIFI_USER:-testuser}"
PASS="${WIFI_PASS:-testpass123}"
EAP_METHOD="${EAP_METHOD:-PEAP}"   # PEAP or TTLS
PHASE2="${PHASE2:-auth=MSCHAPV2}"
CA_CERT="${CA_CERT:-/certs/ca.crt}"

mkdir -p /evidence

cat > /tmp/wpa.conf <<EOF
ctrl_interface=/run/wpa_supplicant
update_config=0
ap_scan=1

network={
  ssid="${SSID}"
  key_mgmt=WPA-EAP
  eap=${EAP_METHOD}
  identity="${USER}"
  password="${PASS}"
  phase2="${PHASE2}"
  ca_cert="${CA_CERT}"
}
EOF

echo "[victim] NOTE: This victim is a wired container; it validates RADIUS/EAP config only." | tee /evidence/victim_notice.txt
echo "[victim] wpa_supplicant config written to /tmp/wpa.conf" | tee /evidence/victim_status.txt

# We don't have a real WiFi radio in-container. Run wpa_supplicant in config-test mode to avoid touching any real victim device.
echo "[victim] Dry-run parse check for wpa_supplicant config..." | tee -a /evidence/victim_status.txt
wpasupplicant -t -c /tmp/wpa.conf >/evidence/wpa_parse.log 2>&1 || true

echo "[victim] Done. Inspect /evidence/*.log" | tee -a /evidence/victim_status.txt
sleep infinity

