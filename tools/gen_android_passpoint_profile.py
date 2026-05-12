#!/usr/bin/env python3
# flake8: noqa: E501
"""
Generate Android Passpoint/EAP-SIM provisioning artifacts for the Telkomsel lab.

The generated JSON is intentionally explicit about Android privilege levels:
normal apps can suggest/configure with user or carrier approval, while silent
installation requires carrier privilege, device-owner/MDM privilege, system
privilege, or a rooted lab device path.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from pathlib import Path


DEFAULT_FQDN = "wlan.mnc010.mcc510.3gppnetwork.org"
DEFAULT_FRIENDLY_NAME = "Telkomsel Lab"
DEFAULT_MCCMNC = "51010"


@dataclass(frozen=True)
class AndroidPasspointProfile:
    fqdn: str
    friendly_name: str
    realm: str
    mccmnc: str
    eap_method: str
    phase2_method: str
    expected_ssid: str
    notes: list[str]
    android_install_paths: dict[str, str]


def build_profile(args: argparse.Namespace) -> AndroidPasspointProfile:
    return AndroidPasspointProfile(
        fqdn=args.fqdn,
        friendly_name=args.friendly_name,
        realm=args.realm,
        mccmnc=args.mccmnc,
        eap_method=args.eap_method,
        phase2_method="NONE",
        expected_ssid=args.ssid,
        notes=[
            "AP cannot force SIM credential selection; Android must own/provision the Passpoint credential.",
            "For EAP-SIM/EAP-AKA suggestions on modern Android, carrier-signed/privileged paths are the realistic silent path.",
            "Normal app provisioning may require user approval and may be rejected for SIM-based enterprise suggestions.",
            "Do not store real IMSI/Ki/OPc/authentication vectors in this profile.",
        ],
        android_install_paths={
            "carrier_privileged_app": "Silent-capable when APK signing certificate is authorized by the SIM/carrier privileges.",
            "device_owner_mdm": "Silent-capable in managed-device lab flows if the MDM/device-owner has WiFi policy privileges.",
            "system_privileged_app": "Silent-capable on custom ROM/OEM lab build with NETWORK_SETTINGS-like privileges.",
        },
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate Android Passpoint EAP-SIM profile metadata."
    )
    parser.add_argument("--ssid", default="LAB-HS20")
    parser.add_argument("--fqdn", default=DEFAULT_FQDN)
    parser.add_argument("--realm", default=DEFAULT_FQDN)
    parser.add_argument("--friendly-name", default=DEFAULT_FRIENDLY_NAME)
    parser.add_argument("--mccmnc", default=DEFAULT_MCCMNC)
    parser.add_argument("--eap-method", default="SIM", choices=["SIM", "AKA", "AKA_PRIME"])
    parser.add_argument(
        "--out",
        type=Path,
        default=Path("profiles/android_passpoint_telkomsel.json"),
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    profile = build_profile(args)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(asdict(profile), indent=2) + "\n", encoding="utf-8")
    print(args.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
