"""Tests for the authoritative SessionKey generated-artifact manifest."""

import json
from pathlib import Path

from tools.verify_session_auth_artifacts import DEFAULT_MANIFEST, verify


def _write_manifest(path: Path, document: dict[str, object]) -> None:
    path.write_text(json.dumps(document), encoding="utf-8")


def test_checked_in_artifacts_match_manifest() -> None:
    assert verify() == []


def test_changed_checksum_has_actionable_error(tmp_path: Path) -> None:
    document = json.loads(DEFAULT_MANIFEST.read_text(encoding="utf-8"))
    document["artifacts"][0]["sha256"] = "0" * 64
    manifest = tmp_path / "artifacts.json"
    _write_manifest(manifest, document)

    errors = verify(manifest)
    assert any("SHA-256 mismatch" in error for error in errors)


def test_missing_manifest_entry_is_reported(tmp_path: Path) -> None:
    document = json.loads(DEFAULT_MANIFEST.read_text(encoding="utf-8"))
    removed = document["artifacts"].pop()["path"]
    manifest = tmp_path / "artifacts.json"
    _write_manifest(manifest, document)

    errors = verify(manifest)
    assert f"unmanifested generated artifact: {removed}" in errors
