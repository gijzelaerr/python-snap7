#!/usr/bin/env python3
"""Verify the SessionKey generated-artifact inventory, sizes, and SHA-256 hashes."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MANIFEST = REPOSITORY_ROOT / "s7commplus/session_auth/artifacts.json"
GENERATED_ROOT = REPOSITORY_ROOT / "s7commplus/session_auth/family0/_generated"


def _is_artifact(path: Path) -> bool:
    return (
        path.suffix == ".bin"
        or path.name == "_constants.py"
        or (path.suffix == ".py" and (path.name.startswith("monolith") or path.name.startswith("part")))
    )


def _load_manifest(path: Path) -> dict[str, Any]:
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"cannot read manifest {path}: {exc}") from exc
    if document.get("schema_version") != 1 or not isinstance(document.get("artifacts"), list):
        raise ValueError("manifest must use schema_version 1 and contain an artifacts list")
    return document


def verify(manifest_path: Path = DEFAULT_MANIFEST) -> list[str]:
    """Return actionable validation errors; an empty list means success."""
    try:
        document = _load_manifest(manifest_path)
    except ValueError as exc:
        return [str(exc)]

    errors: list[str] = []
    declared: set[str] = set()
    required = {"path", "category", "upstream_source", "generation", "size", "sha256"}
    for index, artifact in enumerate(document["artifacts"]):
        if not isinstance(artifact, dict) or not required.issubset(artifact):
            errors.append(f"artifact entry {index} is missing required fields: {sorted(required)}")
            continue
        relative = artifact["path"]
        if not isinstance(relative, str) or relative in declared:
            errors.append(f"artifact entry {index} has an invalid or duplicate path: {relative!r}")
            continue
        declared.add(relative)
        target = (REPOSITORY_ROOT / relative).resolve()
        try:
            target.relative_to(GENERATED_ROOT.resolve())
        except ValueError:
            errors.append(f"manifest path is outside the generated artifact directory: {relative}")
            continue
        if not target.is_file():
            errors.append(f"missing generated artifact: {relative}")
            continue
        data = target.read_bytes()
        actual_hash = hashlib.sha256(data).hexdigest()
        if artifact["size"] != len(data):
            errors.append(f"size mismatch for {relative}: manifest={artifact['size']}, actual={len(data)}")
        if artifact["sha256"] != actual_hash:
            errors.append(f"SHA-256 mismatch for {relative}: manifest={artifact['sha256']}, actual={actual_hash}")

    actual = {
        path.relative_to(REPOSITORY_ROOT).as_posix()
        for path in GENERATED_ROOT.rglob("*")
        if path.is_file() and _is_artifact(path)
    }
    for relative in sorted(actual - declared):
        errors.append(f"unmanifested generated artifact: {relative}")
    for relative in sorted(declared - actual):
        errors.append(f"manifest entry is not a generated runtime artifact: {relative}")
    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    args = parser.parse_args(argv)
    errors = verify(args.manifest)
    if errors:
        print("SessionKey artifact verification failed:", file=sys.stderr)
        for error in errors:
            print(f"  - {error}", file=sys.stderr)
        print(
            "Regenerate the affected output from the pinned HarpoS7 revision or update artifacts.json with reviewed provenance.",
            file=sys.stderr,
        )
        return 1
    print("Verified all SessionKey generated artifacts against artifacts.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
