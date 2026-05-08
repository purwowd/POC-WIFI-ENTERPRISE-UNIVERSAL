## POC-WIFI-ENTERPRISE-UNIVERSAL

Harness lab untuk **WPA2-Enterprise (802.1X)** yang kompatibel luas (Android + iOS) dengan **PEAP/MSCHAPv2** (default) dan opsi **TTLS/PAP**.

Tujuan utamanya: device bisa join tanpa perlu "pilih EAP method" secara manual dengan cara **install profile** (iOS `.mobileconfig`) / **provisioning** (Android).

### Topology
- `ap` : hostapd (AP) → forward auth ke RADIUS
- `radius` : FreeRADIUS (EAP-PEAP / EAP-TTLS), self-signed CA + server cert (lab)
- `victim` : container client (tidak install apa pun di Android/iOS). Dipakai untuk validasi config & evidence logging.

### Requirements
- Linux host dengan WiFi adapter yang support **AP mode** (hostapd)
- Docker + docker compose
- Interface AP dedicated (contoh `wlan1`) tidak di-manage NetworkManager

### Catatan Platform (penting)
- **Linux (native / VM)**: full harness (`ap`+`radius`+`victim`) bisa dijalankan.
- **macOS + Docker Desktop**: **tidak bisa** menjalankan `ap` (hostapd + `network_mode: host` + akses radio Wi‑Fi). Di macOS kamu hanya bisa menjalankan `radius` + `victim` untuk validasi konfigurasi EAP/RADIUS.

Kalau kamu pakai macOS tapi ingin AP beneran:
- Jalankan **Linux VM** (atau host Linux) dan lakukan **USB passthrough** adapter Wi‑Fi ke VM.

### Quick start
0) (Linux) Pastikan adapter support AP mode dan kamu tahu interface Wi‑Fi-nya:

```bash
iw dev
iw list | sed -n '/Supported interface modes:/,/Band /p' | sed -n '1,80p'
```

Pastikan ada `AP` di “Supported interface modes”.

1) Edit `configs/hostapd.conf` → set `interface=...`, `ssid=...`, `channel=...`
2) Jalankan:

```bash
cd pocs/POC-WIFI-ENTERPRISE-UNIVERSAL
docker compose up --build
```

Kalau host kamu pakai NetworkManager dan interface Wi‑Fi direbut NM, disable NM untuk interface AP (contoh `wlan1`):

```bash
nmcli dev set wlan1 managed no
```

3) Kalau kamu *tidak boleh* install apa pun di device victim:
- **Android (disarankan)**: pakai QR Wi‑Fi Enterprise (tanpa install profile)
  - Edit kredensial di `profiles/android_wifi_qr.txt`, atau generate otomatis:
    - `python3 tools/gen_android_wifi_qr.py --ssid LAB-ENTERPRISE --eap PEAP --phase2 MSCHAPV2 --user testuser --password testpass123 --out profiles/android_wifi_qr.txt --png evidence/android_wifi_qr.png`
  - Kalau mau generate PNG, install dependency:
    - `python3 -m pip install -r tools/requirements.txt`
  - Buka `evidence/android_wifi_qr.png` di layar attacker, lalu di Android victim:
    - **Settings → Network & internet → Internet/Wi‑Fi → Add network / Scan QR**
    - atau fitur “Scan QR” dari panel Wi‑Fi (tergantung vendor/versi).

- **iOS**: umumnya tidak support join WPA2‑Enterprise via QR tanpa profile.
  - Opsi tanpa install profile: join manual sekali (Settings → Wi‑Fi → pilih SSID → isi username/password → trust CA / server name sesuai lab).
  - Kalau butuh auto-join yang rapih/berulang: pakai `profiles/ios_peap.mobileconfig`.

- **Container validation (tanpa sentuh device)**: jalankan `victim` container untuk validasi config & evidence (parse config `wpa_supplicant`).

Kalau kamu memang pakai device milikmu sendiri (bukan victim) dan boleh provisioning:
- iOS: `profiles/ios_peap.mobileconfig` (ubah SSID + server name)
- Android: pakai QR `profiles/android_wifi_qr.txt` (ubah SSID + user/pass)

### Run mode (macOS / tanpa AP)
Kalau kamu hanya mau uji FreeRADIUS + EAP config (tanpa hostapd/AP), jalankan:

```bash
docker compose up -d --build radius victim
docker compose logs -f radius
```

Ini tidak mem-broadcast SSID; hanya validasi bahwa stack RADIUS/EAP berjalan dan config `wpa_supplicant` valid.

### Default test credentials
- username: `testuser`
- password: `testpass123`

### Evidence
Log FreeRADIUS akan menunjukkan authentication + identity. Simpan output/log ke `evidence/` kalau perlu.

