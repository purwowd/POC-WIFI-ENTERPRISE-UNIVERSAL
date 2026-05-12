## POC-WIFI-ENTERPRISE-UNIVERSAL

Harness lab untuk validasi **WiFi Passpoint / Hotspot 2.0 (HS2.0) + WPA2-Enterprise + EAP-SIM** dengan stack yang realistis:

```text
Client lab owned by researcher
  -> WiFi Passpoint / HS2.0
hostapd AP
  -> 802.1X / RADIUS
FreeRADIUS
  -> EAP-SIM test vectors or lab AuC/SIM backend
```

PoC ini sengaja tidak memakai EAPHammer sebagai core. Untuk EAP-SIM/Hotspot 2.0, faktor penentu client auto memilih EAP-SIM adalah profile/credential client yang match dengan iklan ANQP/HS2.0 AP dan backend AAA, bukan paksaan dari AP.

### Yang Berubah Dari Versi PEAP/TTLS

- Default SSID menjadi `LAB-HS20`.
- `hostapd` sekarang mengiklankan 802.11u Interworking, HS2.0, NAI realm, operator name, domain, dan 3GPP PLMN Telkomsel `510/10`.
- `FreeRADIUS` default ke `EAP-SIM` dan menyertakan placeholder GSM triplets untuk identity lab `1001010000000001`.
- Victim utama diasumsikan **HP Android lab fisik** dengan SIM Telkomsel. `victim` container hanya mode opsional untuk validasi parsing config.
- PEAP/TTLS masih tersedia sebagai fallback config, tetapi bukan flow utama.

### Catatan Penting EAP-SIM

EAP-SIM butuh authentication vector dari SIM/AuC. Secret seperti `Ki` atau `OPc` tidak dikirim lewat jaringan dan tidak boleh dimasukkan ke AP. Untuk lab resmi, gunakan salah satu:

- SIM/test SIM yang kamu kontrol.
- GSM triplet test vector yang sesuai dengan SIM lab.
- hostapd `eap_sim_db` / HLR-AuC gateway lab.
- Operator-like backend dengan programmable SIM, HSS/AuC, Open5GS/srsRAN, dan RADIUS/EAP-SIM-AKA gateway.

File `radius/conf/users` berisi triplet dummy untuk wiring config. Triplet itu berguna untuk bootstrapping FreeRADIUS, tetapi tidak akan membuat SIM Telkomsel komersial berhasil autentikasi. Untuk SIM operator publik, AP lokal hanya bisa mengiklankan PLMN/realm; autentikasi sukses tetap butuh jalur AAA/operator atau vector dari backend yang memang kamu kontrol.

### Opsi Setup

#### Opsi A: Lab Paling Aman dan Controllable

Gunakan 1 laptop Linux, 1 adapter WiFi AP mode, `hostapd`, `FreeRADIUS`, `wpa_supplicant`, dan EAP-SIM test vector.

Cocok untuk validasi:

- AP advertise HS2.0/ANQP.
- Client profile hanya mengizinkan EAP-SIM.
- EAP identity exchange terjadi.
- RADIUS menerima request EAP-SIM.
- Backend mengirim challenge dari test vector.

Kelemahannya: ini bukan test dengan HP consumer + SIM operator, tetapi paling enak untuk debug.

#### Opsi B: Lab Dengan Android Telkomsel Milik Sendiri

Gunakan AP Linux + `hostapd` HS2.0 + Android milik sendiri dengan SIM Telkomsel. Default config PoC mengiklankan:

- MCC/MNC: `510/10`
- Realm 3GPP: `wlan.mnc010.mcc510.3gppnetwork.org`
- Friendly name: `Telkomsel Lab`

Ini cocok untuk melihat apakah HP membaca ANQP/HS2.0, apakah carrier/Passpoint stack mencoba EAP-SIM/AKA, dan apakah RADIUS lokal menerima identity exchange. Jangan ekspektasikan authentication success dengan FreeRADIUS lokal kecuali kamu punya AAA gateway/vector resmi untuk SIM tersebut.

Kelemahannya: Android consumer sering tidak memberi kontrol penuh untuk provisioning EAP-SIM manual kecuali lewat carrier profile, MDM, Passpoint profile, OEM API, atau mekanisme provisioning vendor.

#### Opsi C: Operator-like Lab

Gunakan programmable SIM, Open5GS/srsRAN core lab, AuC/HSS data sendiri, AP HS2.0, dan RADIUS/EAP-SIM-AKA gateway.

Ini paling dekat dengan riset WiFi offload/cellular-authenticated WiFi, tetapi setup jauh lebih berat.

### Requirements

- Linux host atau Linux VM dengan USB passthrough WiFi adapter.
- Docker + Docker Compose.
- WiFi adapter yang stabil untuk AP mode.
- Interface AP dedicated, contoh `wlan1`, tidak dikelola NetworkManager.
- Optional: programmable SIM / sysmocom SIM untuk operator-like lab.

Software utama:

- `hostapd`: AP + 802.11u/HS2.0 advertisement.
- `dnsmasq`: DHCP jika AP dipakai sebagai gateway internet lab.
- `FreeRADIUS`: AAA backend.
- `wpa_supplicant`: Linux client debug.
- `tcpdump` / Wireshark: EAPOL, RADIUS, ANQP debug.

### Catatan Platform

- **Linux native / VM**: jalankan `ap` + `radius`, lalu gunakan HP fisik sebagai victim/client.
- **macOS + Docker Desktop**: tidak bisa menjalankan AP karena `hostapd`, `network_mode: host`, dan akses radio WiFi butuh Linux. Di macOS jalankan `radius` dan optional `victim` profile untuk validasi config saja.

Kalau memakai macOS dan butuh AP beneran, jalankan Linux VM atau host Linux lalu lakukan USB passthrough adapter WiFi ke VM.

### Quick Start

0. Pastikan adapter support AP mode:

```bash
iw dev
iw list | sed -n '/Supported interface modes:/,/Band /p' | sed -n '1,80p'
```

Pastikan ada `AP` di "Supported interface modes".

1. Edit `configs/hostapd.conf` kalau interface WiFi AP kamu bukan `wlan1`:

- `interface=wlan1`
- `ssid=LAB-HS20`
- `channel=6`
- `country_code=ID`
- `domain_name=wlan.mnc010.mcc510.3gppnetwork.org`
- `anqp_3gpp_cell_net=510,10`
- `nai_realm=...wlan.mnc010.mcc510.3gppnetwork.org...`

2. Kalau NetworkManager merebut interface AP:

```bash
nmcli dev set wlan1 managed no
```

3. Preflight PoC:

```bash
cd pocs/POC-WIFI-ENTERPRISE-UNIVERSAL
python3 poc.py --mode check --interface wlan1 --output evidence/telkomsel-check.json
```

4. Jalankan AP + RADIUS di Linux:

```bash
cd pocs/POC-WIFI-ENTERPRISE-UNIVERSAL
python3 poc.py --mode start --interface wlan1 \
  --confirm-real-phone-lab \
  --confirm-rf-lab \
  --output evidence/telkomsel-start.json
```

Command manual ekuivalen:

```bash
docker compose up -d --build radius ap
docker compose logs -f radius ap
```

5. Gunakan HP Android lab sebagai client:

- Pastikan SIM Telkomsel aktif.
- Hapus saved network lama dengan SSID `LAB-HS20`.
- Aktifkan WiFi dan biarkan device scan SSID/Passpoint.
- Jika Android tidak auto-select, itu biasanya karena carrier/Passpoint profile tidak mengizinkan manual EAP-SIM untuk SSID ini.
- Runbook detail: `profiles/android_telkomsel_runbook.md`.

6. Capture evidence saat HP mencoba scan/connect:

```bash
python3 poc.py --mode capture --interface wlan1 --sudo --capture-seconds 120 \
  --output evidence/telkomsel-capture.json
```

Atau start + capture dalam satu command:

```bash
python3 poc.py --mode full --interface wlan1 --sudo --capture-seconds 120 \
  --confirm-real-phone-lab \
  --confirm-rf-lab \
  --output evidence/telkomsel-full.json
```

`poc.py` juga menyimpan `docker compose logs radius ap` ke `evidence/telkomsel-docker-logs-*.log` dan mencoba mendeteksi identity EAP-SIM:

- `permanent_eap_sim_identity`: value berupa `1 + IMSI`, contoh pola Telkomsel `151010...`.
- `anonymous_identity`: HP memakai outer identity anonim; IMSI tidak terlihat.
- `pseudonym_or_realm_identity`: carrier/device memakai pseudonym.

Hasil JSON meredaksi identity secara default. Kalau benar-benar perlu full value di JSON untuk lab notebook lokal:

```bash
python3 poc.py --mode capture --interface wlan1 --sudo --capture-seconds 120 \
  --no-redact-identities \
  --output evidence/telkomsel-capture-full-identity.json
```

Raw PCAP/log tetap bisa mengandung IMSI penuh kalau HP memang mengirim permanent identity.

7. Stop hotspot:

```bash
python3 poc.py --mode stop
```

8. Jalankan mode config-only di macOS atau tanpa AP:

```bash
docker compose --profile docker-victim up -d --build radius victim
docker compose logs -f radius
```

Mode ini tidak broadcast SSID. Ia hanya memastikan FreeRADIUS config dan profil `wpa_supplicant` EAP-SIM bisa dibuat/di-parse.

### Konfigurasi AP

Bagian penting `hostapd`:

```text
ieee8021x=1
wpa=2
wpa_key_mgmt=WPA-EAP
rsn_pairwise=CCMP

auth_server_addr=10.88.0.10
auth_server_port=1812
auth_server_shared_secret=labsecret

interworking=1
access_network_type=2
internet=1

hs20=1
hs20_oper_friendly_name=eng:Telkomsel Lab
domain_name=wlan.mnc010.mcc510.3gppnetwork.org
anqp_3gpp_cell_net=510,10
nai_realm=0,wlan.mnc010.mcc510.3gppnetwork.org,5[5:6]
```

`nai_realm` dan `anqp_3gpp_cell_net` harus match dengan profile client dan SIM/operator lab. Default PoC memakai PLMN Telkomsel `510/10`.

### Konfigurasi Client

Linux debug profile tersedia di `profiles/linux_eap_sim.conf`.

Untuk client auto EAP-SIM, profile harus punya:

- SSID / Passpoint credential untuk `LAB-HS20`.
- Credential type SIM/USIM.
- EAP method SIM saja, atau AKA/AKA' sesuai lab.
- Realm `wlan.mnc010.mcc510.3gppnetwork.org`.
- MCC/MNC `510/10` untuk Telkomsel.
- Auto-join enabled.

Kalau profile masih mengizinkan PEAP/TTLS, client bisa memilih metode lain. Untuk validasi EAP-SIM, jangan dibuat multi-option.

### Backend EAP-SIM

Backend yang bisa dipakai:

1. FreeRADIUS dengan EAP-SIM test vectors.
2. hostapd internal EAP server + `eap_sim_db`.
3. HLR/AuC gateway lab.
4. Operator-like backend dengan programmable SIM.

Default AP mengiklankan Telkomsel, tetapi default RADIUS masih memakai opsi 1 untuk bootstrap FreeRADIUS:

- Identity: `1001010000000001`
- IMSI: `001010000000001`
- Realm: `lab.operator.local`
- PLMN: `001/01`
- Triplet: lihat `radius/conf/users`

Itu adalah test identity, bukan identity Telkomsel. Jangan masukkan IMSI/Ki/OPc real ke repo. Untuk HP Telkomsel komersial, target realistis tanpa kerja sama AAA adalah melihat discovery, EAP identity, dan failure reason di FreeRADIUS/hostapd.

### Debug Flow

Saat berhasil, urutan yang dicari:

1. Client scan AP.
2. Client membaca ANQP/HS2.0 info.
3. Client mencocokkan realm/operator/MCC/MNC.
4. Client connect WPA-Enterprise.
5. EAPOL mulai.
6. Identity exchange.
7. RADIUS menerima EAP-SIM.
8. Backend mengirim challenge.
9. Client/SIM menghitung response.
10. Authentication sukses hanya jika backend punya vector/AAA yang valid. Dengan SIM Telkomsel komersial + FreeRADIUS lokal, hasil realistis biasanya berhenti di identity/challenge atau Access-Reject.

Capture EAPOL dan RADIUS:

```bash
tcpdump -i wlan1 -vvv ether proto 0x888e
tcpdump -i any -vvv 'udp port 1812 or udp port 1813'
```

Log penting:

```bash
hostapd -dd configs/hostapd.conf
freeradius -X
wpa_supplicant -dd -i wlan0 -c profiles/linux_eap_sim.conf
```

ANQP query dari Linux client:

```bash
wpa_cli -i wlan0 scan
wpa_cli -i wlan0 scan_results
wpa_cli -i wlan0 anqp_get <BSSID> nai_realm
wpa_cli -i wlan0 anqp_get <BSSID> 3gpp
```

### Kalau Client Tidak Auto EAP-SIM

Cek ini dulu:

1. Client punya Passpoint/EAP-SIM profile.
2. Profile hanya mengizinkan EAP-SIM, bukan PEAP/TTLS.
3. Realm client sama dengan realm AP.
4. MCC/MNC cocok dengan `anqp_3gpp_cell_net`.
5. AP benar-benar advertise HS2.0/ANQP.
6. RADIUS menerima request dari hostapd.
7. Backend support EAP-SIM.
8. Untuk SIM Telkomsel komersial, ada AAA/carrier path yang valid; FreeRADIUS lokal dengan triplet dummy tidak cukup.
9. Device tidak memaksa privacy/pseudonym identity yang belum dipetakan.
10. Tidak ada saved network lama dengan SSID sama.

### Rekomendasi Iterasi

Phase 1:

- Linux client dengan `wpa_supplicant`.
- `hostapd` AP.
- `FreeRADIUS -X`.
- EAP-SIM test vector.

Phase 2:

- Ganti client ke Android Telkomsel milik sendiri.
- Cek apakah AP Telkomsel lab muncul/terseleksi dari carrier/Passpoint stack.
- Cek apakah FreeRADIUS menerima EAP-SIM identity exchange.
- Perlakukan Access-Reject sebagai expected result kalau belum ada AAA gateway resmi.

Phase 3:

- Masuk programmable SIM / Open5GS / srsRAN kalau perlu operator-like lab.

### Legacy PEAP/TTLS Artefacts

Artefak lama masih disimpan untuk fallback:

- `profiles/ios_peap.mobileconfig`
- `profiles/android_wifi_qr.txt`
- `tools/gen_android_wifi_qr.py`

Android WiFi Enterprise QR cocok untuk PEAP/TTLS lab, bukan mekanisme provisioning utama untuk Passpoint EAP-SIM.

### Evidence

Simpan log/capture ke `evidence/`:

- `hostapd` debug log.
- `freeradius -X` output.
- `telkomsel-docker-logs-*.log` dari `radius` dan `ap`.
- `wpa_supplicant -dd` output.
- PCAP EAPOL dan RADIUS.

Jangan commit real SIM material, Ki/OPc, authentication vector produksi, IMSI penuh, atau log mentah yang belum disanitasi.

