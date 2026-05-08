## POC-WIFI-ENTERPRISE-UNIVERSAL

Harness lab untuk **WPA2-Enterprise (802.1X)** yang kompatibel luas (Android + iOS) dengan **PEAP/MSCHAPv2** (default) dan opsi **TTLS/PAP**.

Tujuan utamanya: device bisa join tanpa perlu "pilih EAP method" secara manual dengan cara **install profile** (iOS `.mobileconfig`) / **provisioning** (Android).

### Topology
- `ap` : hostapd (AP) → forward auth ke RADIUS
- `radius` : FreeRADIUS (EAP-PEAP / EAP-TTLS), self-signed CA + server cert (lab)
- `victim` : container client (tidak install apa pun di Android/iOS). Dipakai untuk validasi config & evidence logging.

### Requirements
- Linux host dengan WiFi adapter yang support **AP mode**
- Docker + docker compose
- Interface AP dedicated (contoh `wlan1`) tidak di-manage NetworkManager

### Quick start
1) Edit `configs/hostapd.conf` → set `interface=...`, `ssid=...`, `channel=...`
2) Jalankan:

```bash
cd pocs/POC-WIFI-ENTERPRISE-UNIVERSAL
docker compose up --build
```

3) Kalau kamu *tidak boleh* install apa pun di device victim:
- Jalankan `victim` container untuk validasi config & evidence.

Kalau kamu memang pakai device milikmu sendiri (bukan victim) dan boleh provisioning:
- iOS: `profiles/ios_peap.mobileconfig` (ubah SSID + server name)
- Android: pakai QR `profiles/android_wifi_qr.txt` (ubah SSID + user/pass)

### Default test credentials
- username: `testuser`
- password: `testpass123`

### Evidence
Log FreeRADIUS akan menunjukkan authentication + identity. Simpan output/log ke `evidence/` kalau perlu.

