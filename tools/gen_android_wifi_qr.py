#!/usr/bin/env python3
"""
gen_android_wifi_qr.py

Generate an Android-friendly "WiFi QR" payload string for WPA2-Enterprise
(802.1X) PEAP/TTLS lab fallback and optionally render it as a QR PNG.

This is not a Passpoint/EAP-SIM provisioning mechanism. Android EAP-SIM
usually needs carrier profile, MDM, Passpoint provisioning, OEM API, or
another managed credential path.

Output format (commonly supported on Android 10+; vendor-dependent):
  WIFI:T:WPA2-EAP;S:<ssid>;E:<eap>;PH2:<phase2>;A:<anon>;I:<identity>;H:false;
  U:<user>;P:<password>;;

Examples:
  python3 tools/gen_android_wifi_qr.py --ssid LAB-ENTERPRISE --eap PEAP \
    --phase2 MSCHAPV2 --user testuser --password testpass123 \
    --out profiles/android_wifi_qr.txt --png evidence/android_wifi_qr.png
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class WifiEnterpriseQr:
    ssid: str
    eap: str
    phase2: str
    user: str
    password: str
    hidden: bool = False
    anonymous_identity: str = ""
    identity: str = ""

    def to_payload(self) -> str:
        # Keep ordering stable for ease of diff/repro.
        hidden_flag = "true" if self.hidden else "false"
        # Fields A and I are seen in the wild; some Android builds ignore them.
        return (
            "WIFI:"
            f"T:WPA2-EAP;"
            f"S:{escape(self.ssid)};"
            f"E:{escape(self.eap)};"
            f"A:{escape(self.anonymous_identity)};"
            f"I:{escape(self.identity)};"
            f"PH2:{escape(self.phase2)};"
            f"H:{hidden_flag};"
            f"U:{escape(self.user)};"
            f"P:{escape(self.password)};;"
        )


def escape(value: str) -> str:
    r"""
    Escape WiFi QR special chars per common de-facto convention.
    (Backslash-escape: \\, \;, \,, \:)
    """
    return (
        value.replace("\\", "\\\\")
        .replace(";", r"\;")
        .replace(",", r"\,")
        .replace(":", r"\:")
    )


def render_png(payload: str, out_path: Path) -> None:
    try:
        import qrcode  # type: ignore
    except Exception as e:  # pragma: no cover
        raise SystemExit(
            "Missing dependency for PNG rendering. Install with:\n"
            "  python3 -m pip install 'qrcode[pil]'\n"
            f"Original import error: {e}"
        )

    qr = qrcode.QRCode(border=2)
    qr.add_data(payload)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(out_path)


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Generate Android WPA2-Enterprise PEAP/TTLS WiFi QR payload."
    )
    p.add_argument("--ssid", required=True, help="WiFi SSID")
    p.add_argument(
        "--eap",
        default="PEAP",
        help="EAP method (PEAP or TTLS). Default: PEAP",
    )
    p.add_argument(
        "--phase2",
        default="MSCHAPV2",
        help=(
            "Inner/phase2 method marker for QR (e.g., MSCHAPV2 or PAP). "
            "Default: MSCHAPV2"
        ),
    )
    p.add_argument("--user", required=True, help="Username / identity")
    p.add_argument("--password", required=True, help="Password")
    p.add_argument("--anonymous", default="", help="Anonymous identity (optional)")
    p.add_argument(
        "--identity",
        default="",
        help="Explicit identity field (optional; usually empty)",
    )
    p.add_argument("--hidden", action="store_true", help="Set H:true for hidden SSID")
    p.add_argument(
        "--out",
        type=Path,
        default=None,
        help="Write payload string to a file (txt)",
    )
    p.add_argument(
        "--png",
        type=Path,
        default=None,
        help="Render QR code to PNG (requires qrcode[pil])",
    )
    return p.parse_args()


def main() -> int:
    args = parse_args()

    if args.eap.upper() in {"SIM", "AKA", "AKA'"}:
        raise SystemExit(
            "Android WiFi QR is not a reliable Passpoint/EAP-SIM provisioning "
            "path. Use a Passpoint/MDM/carrier profile for EAP-SIM."
        )

    qr = WifiEnterpriseQr(
        ssid=args.ssid,
        eap=args.eap.upper(),
        phase2=args.phase2.upper(),
        user=args.user,
        password=args.password,
        hidden=bool(args.hidden),
        anonymous_identity=args.anonymous,
        identity=args.identity,
    )
    payload = qr.to_payload()

    print(payload)

    if args.out is not None:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(payload + "\n", encoding="utf-8")

    if args.png is not None:
        render_png(payload, args.png)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
