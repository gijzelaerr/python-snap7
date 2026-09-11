#!/usr/bin/env python3
"""Run the safe real-PLC acceptance profile and produce shareable artifacts."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
from pathlib import Path

import pytest


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plc-ip", required=True, help="PLC address (used for connection only; never written to reports)")
    parser.add_argument("--protocol", required=True, choices=("legacy_s7", "s7commplus"))
    parser.add_argument("--tester", required=True, help="GitHub handle")
    parser.add_argument("--plc-family", required=True)
    parser.add_argument("--plc-model", required=True)
    parser.add_argument("--plc-firmware", required=True)
    parser.add_argument("--plc-order-code", default="")
    parser.add_argument("--plc-security-mode", required=True)
    parser.add_argument("--plc-tia-configuration", default="")
    parser.add_argument("--plc-port", type=int, default=102)
    parser.add_argument("--plc-rack", type=int, default=0)
    parser.add_argument("--plc-slot", type=int, default=1)
    parser.add_argument("--plc-db-read", type=int, default=1)
    parser.add_argument("--plc-db-write", type=int, default=2)
    parser.add_argument("--allow-write", action="store_true", help="Also run scratch writes with verified restoration")
    parser.add_argument("--allow-admin", action="store_true", help="Also run disruptive administrative scenarios")
    parser.add_argument("--output-dir", type=Path, default=Path("real-plc-results"))
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    stem = f"real-plc-{args.protocol}-{stamp}"
    junit = args.output_dir / f"{stem}.junit.xml"
    report = args.output_dir / f"{stem}.json"
    marker = "smoke"
    if args.allow_write:
        marker += " or write"
    if args.allow_admin:
        marker += " or administrative"
    pytest_args = [
        "tests/real_plc/test_acceptance.py",
        "--e2e",
        "-v",
        "--gherkin-terminal-reporter",
        "-m",
        marker,
        f"--junitxml={junit}",
        f"--plc-report-json={report}",
        f"--plc-ip={args.plc_ip}",
        f"--plc-protocol={args.protocol}",
        f"--tester={args.tester}",
        f"--plc-family={args.plc_family}",
        f"--plc-model={args.plc_model}",
        f"--plc-firmware={args.plc_firmware}",
        f"--plc-order-code={args.plc_order_code}",
        f"--plc-security-mode={args.plc_security_mode}",
        f"--plc-tia-configuration={args.plc_tia_configuration}",
        f"--plc-port={args.plc_port}",
        f"--plc-rack={args.plc_rack}",
        f"--plc-slot={args.plc_slot}",
        f"--plc-db-read={args.plc_db_read}",
        f"--plc-db-write={args.plc_db_write}",
    ]
    if args.allow_write:
        pytest_args.append("--allow-plc-write")
    if args.allow_admin:
        pytest_args.append("--allow-plc-admin")
    return pytest.main(pytest_args)


if __name__ == "__main__":
    raise SystemExit(main())
