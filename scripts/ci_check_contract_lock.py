#!/usr/bin/env python3
"""CI/local guardrail: validate contracts.lock.json shape without mutating it."""

from __future__ import annotations

import json
import sys
from pathlib import Path

REQUIRED_FIELDS = (
    "contract_repo",
    "contract_ref_type",
    "contract_sha",
    "generated_at",
    "generated_by",
)


def find_lock_path() -> Path:
    repo_root = Path(__file__).resolve().parents[1]
    return repo_root / "contracts.lock.json"


def validate_lock(lock_path: Path) -> list[str]:
    errors: list[str] = []
    if not lock_path.exists():
        errors.append(f"Missing lock file: {lock_path}")
        return errors

    try:
        raw = json.loads(lock_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        errors.append(f"Invalid JSON in {lock_path}: {exc}")
        return errors

    if not isinstance(raw, dict):
        errors.append("contracts.lock.json must be a JSON object.")
        return errors

    for field in REQUIRED_FIELDS:
        if field not in raw:
            errors.append(f"Missing required field: {field}")

    if errors:
        return errors

    if raw.get("contract_ref_type") != "git_sha":
        errors.append("Field 'contract_ref_type' must be 'git_sha'.")

    for field in ("contract_repo", "contract_sha", "generated_at", "generated_by"):
        value = raw.get(field)
        if not isinstance(value, str) or not value.strip():
            errors.append(f"Field '{field}' must be a non-empty string.")

    sha = raw.get("contract_sha", "")
    if isinstance(sha, str) and sha.strip():
        if len(sha.strip()) < 7:
            errors.append("Field 'contract_sha' looks invalid (too short).")

    return errors


def main() -> int:
    lock_path = find_lock_path()
    print(f"ci_check_contract_lock: checking {lock_path}")
    errors = validate_lock(lock_path)
    if errors:
        print("ci_check_contract_lock: FAILED", file=sys.stderr)
        for line in errors:
            print(f"  - {line}", file=sys.stderr)
        print(
            "\nRemediation: ensure contracts.lock.json matches the schema expected by "
            "the runtime loader, or run `python scripts/update_contract_lock.py` locally "
            "after reviewing the contract repo SHA (do not commit lock drift blindly).",
            file=sys.stderr,
        )
        return 1

    print("ci_check_contract_lock: OK (required keys present, basic shape valid).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
