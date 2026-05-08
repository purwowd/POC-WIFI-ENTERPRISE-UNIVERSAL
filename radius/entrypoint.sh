#!/usr/bin/env sh
set -eu

SECRET="${RADIUS_CLIENT_SECRET:-labsecret}"
EAP_DEFAULT="${RADIUS_EAP_DEFAULT:-peap}"

CERTDIR=/certs
CADB="${CERTDIR}/ca.key"
CACRT="${CERTDIR}/ca.crt"
SRVKEY="${CERTDIR}/server.key"
SRVCRT="${CERTDIR}/server.crt"

gen_certs() {
  if [ -f "$CACRT" ] && [ -f "$SRVCRT" ] && [ -f "$SRVKEY" ]; then
    echo "[radius] certs already exist in ${CERTDIR}" >&2
    return
  fi

  echo "[radius] generating lab CA + server certs in ${CERTDIR}" >&2
  umask 077

  openssl genrsa -out "$CADB" 2048
  openssl req -x509 -new -nodes -key "$CADB" -sha256 -days 3650 \
    -subj "/C=ID/O=SecurityResearchLab/CN=LAB-RADIUS-CA" \
    -out "$CACRT"

  openssl genrsa -out "$SRVKEY" 2048
  openssl req -new -key "$SRVKEY" \
    -subj "/C=ID/O=SecurityResearchLab/CN=radius.lab" \
    -out "${CERTDIR}/server.csr"

  cat > "${CERTDIR}/server.ext" <<'EOF'
basicConstraints=CA:FALSE
keyUsage = digitalSignature, keyEncipherment
extendedKeyUsage = serverAuth
subjectAltName = @alt_names
[alt_names]
DNS.1 = radius.lab
EOF

  openssl x509 -req -in "${CERTDIR}/server.csr" -CA "$CACRT" -CAkey "$CADB" \
    -CAcreateserial -out "$SRVCRT" -days 825 -sha256 -extfile "${CERTDIR}/server.ext"
  rm -f "${CERTDIR}/server.csr" "${CERTDIR}/server.ext"
}

patch_radius_conf() {
  WORK=/tmp/radius-conf
  rm -rf "$WORK"
  mkdir -p "$WORK"
  cp -a /etc/freeradius/* "$WORK/"

  # Ensure certdir primitives exist for TLS (dh + random).
  mkdir -p "$WORK/certs"
  if [ ! -f "$WORK/certs/random" ]; then
    dd if=/dev/urandom of="$WORK/certs/random" bs=32 count=1 >/dev/null 2>&1 || true
  fi
  if [ ! -f "$WORK/certs/dh" ]; then
    echo "[radius] generating DH params (may take a bit)..." >&2
    # Lab default. Increase to 2048 if you want stronger params.
    openssl dhparam -out "$WORK/certs/dh" 1024 >/dev/null 2>&1 || true
  fi

  # Ensure minimal client definition for AP network.
  cat > "$WORK/clients.conf" <<EOF
client ap-lab {
  ipaddr = 10.88.0.0/24
  secret = ${SECRET}
}
EOF

  # Overlay lab config snippets (kept minimal)
  if [ -d /lab-conf ]; then
    cp -af /lab-conf/authorize "$WORK/authorize" 2>/dev/null || true
    cp -af /lab-conf/authenticate "$WORK/authenticate" 2>/dev/null || true
    cp -af /lab-conf/users "$WORK/users" 2>/dev/null || true
    if [ -d /lab-conf/mods-enabled ]; then
      mkdir -p "$WORK/mods-enabled"
      cp -af /lab-conf/mods-enabled/* "$WORK/mods-enabled/" 2>/dev/null || true
    fi
  fi

  # Set TOP-LEVEL default EAP type only (first occurrence).
  # We intentionally do not rewrite inner sections (peap/ttls) defaults.
  if [ -f "$WORK/mods-enabled/eap" ]; then
    sed -i "0,/^[[:space:]]*default_eap_type[[:space:]]*=/{s/^[[:space:]]*default_eap_type[[:space:]]*=.*/\tdefault_eap_type = ${EAP_DEFAULT}/}" "$WORK/mods-enabled/eap" || true
  fi

  # Point TLS certs to /certs.
  for tls in tls-config tls-common; do
    if [ -f "$WORK/mods-enabled/eap" ]; then
      sed -i "s#\\(ca_file\\s*=\\s*\\).*#\\1${CACRT}#g" "$WORK/mods-enabled/eap" || true
      sed -i "s#\\(certificate_file\\s*=\\s*\\).*#\\1${SRVCRT}#g" "$WORK/mods-enabled/eap" || true
      sed -i "s#\\(private_key_file\\s*=\\s*\\).*#\\1${SRVKEY}#g" "$WORK/mods-enabled/eap" || true
    fi
  done

  echo "$WORK"
}

gen_certs
WORKDIR="$(patch_radius_conf)"

echo "[radius] starting freeradius (default_eap_type=${EAP_DEFAULT})" >&2
exec freeradius -X -d "$WORKDIR"

