# Android Passpoint Auto-Install Options

Goal: make the lab phone auto-select SIM credential for `LAB-HS20` instead of showing the manual PEAP form, with **no runtime user interaction** and **no rooted device**.

## What The AP Can And Cannot Do

The AP can advertise:

- SSID: `LAB-HS20`
- PLMN: `510/10`
- Realm: `wlan.mnc010.mcc510.3gppnetwork.org`
- EAP method: `SIM`

The AP cannot push or force SIM credential selection. Android must already have, or be provisioned with, a Passpoint credential that matches the AP.

## Silent Auto-Install Paths

### 1. Carrier-Privileged App

Best match for Telkomsel SIM auto-selection.

Requirement:

- APK signing certificate is authorized by the SIM/carrier privilege rules.
- App provisions a `PasspointConfiguration` or `WifiNetworkSuggestion` with EAP-SIM/EAP-AKA.

Result:

- Can be silent/automatic on supported Android builds.
- Tied to the SIM/carrier identity.

### 2. Device Owner / MDM

Best no-root path for fully controlled lab phones.

Requirement:

- Factory-reset or managed-device setup.
- Your provisioning app is set as device owner.
- MDM/device-owner uses WiFi policy APIs supported by that Android build/OEM.

Result:

- Can install managed WiFi/Passpoint config without normal user prompts.
- Most reliable when you control the device lifecycle.

### 3. System / Privileged App

Best for custom ROM/OEM lab devices.

Requirement:

- App installed under privileged system partition or signed with platform key.
- Has WiFi management permissions such as network settings privileges.

Result:

- Can use privileged WiFi APIs directly.

## Explicitly Out Of Scope For This PoC

- Root/ADB config-store injection.
- Normal APK flow that prompts the user.
- Manual WiFi UI selection.

With your constraint, the practical default is **Device Owner / MDM** unless you have Telkomsel carrier-privileged signing or a system-privileged lab build.

## Recommended No-Root No-Prompt Lab Path

1. Prepare a lab phone that can be enrolled as device owner.
2. Install/enroll your DPC/MDM provisioning app during device setup.
3. DPC provisions the Passpoint profile with:
   - FQDN: `wlan.mnc010.mcc510.3gppnetwork.org`
   - Realm: `wlan.mnc010.mcc510.3gppnetwork.org`
   - MCC/MNC: `51010`
   - EAP method: `SIM`
4. Start `LAB-HS20`.
5. Android auto-selects the Passpoint profile without opening the manual PEAP form.

## Generate Profile Metadata

```bash
cd pocs/POC-WIFI-ENTERPRISE-UNIVERSAL
python3 tools/gen_android_passpoint_profile.py \
  --out profiles/android_passpoint_telkomsel.json
```

The generated JSON is input metadata for a carrier-privileged app, MDM payload, system app, or root lab injector. It intentionally does not include IMSI, Ki, OPc, or authentication vectors.

## Expected Success Criteria

After provisioning succeeds:

1. Android no longer opens the manual PEAP form for `LAB-HS20`.
2. Android auto-matches `510/10` + `wlan.mnc010.mcc510.3gppnetwork.org`.
3. `hostapd` shows association/EAPOL.
4. `poc-wifi-radius` shows `Access-Request` and EAP identity.
5. `poc.py` JSON reports either `permanent_eap_sim_identity`, `anonymous_identity`, or `pseudonym_or_realm_identity`.
