from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

from .api import (
    build_non_synthetic_preflight_envelope,
    build_pressure_candidate,
    build_synthetic_envelope,
    health,
    ingest_synthetic_event,
    list_events,
    run_non_synthetic_preflight,
)
from .config import RuntimeConfigError
from .contract_loader import ContractLoadError


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    try:
        if args.command == "health":
            return _emit_result(health())
        if args.command == "ingest-synthetic":
            document = _read_json_file(Path(args.json_path))
            envelope = _coerce_synthetic_envelope(document)
            return _emit_result(ingest_synthetic_event(envelope))
        if args.command == "list-events":
            return _emit_result(list_events())
        if args.command == "build-pressure-candidate":
            return _emit_result(build_pressure_candidate())
        if args.command == "non-synthetic-preflight":
            document = _read_json_file(Path(args.json_path))
            envelope = _coerce_non_synthetic_preflight_envelope(document)
            return _emit_result(run_non_synthetic_preflight(envelope))
        if args.command == "refresh-contract-lock":
            return _emit_result(_refresh_contract_lock())
    except (
        FileNotFoundError,
        json.JSONDecodeError,
        RuntimeConfigError,
        ContractLoadError,
        ValueError,
        subprocess.CalledProcessError,
    ) as exc:
        return _emit_result({"ok": False, "error": str(exc)}, exit_code=1)

    return _emit_result({"ok": False, "error": "unknown command"}, exit_code=2)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="exceptions-lake")
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("health")

    ingest_parser = subparsers.add_parser("ingest-synthetic")
    ingest_parser.add_argument("json_path")

    subparsers.add_parser("list-events")
    subparsers.add_parser("build-pressure-candidate")

    preflight_parser = subparsers.add_parser("non-synthetic-preflight")
    preflight_parser.add_argument("json_path")

    subparsers.add_parser("refresh-contract-lock")
    return parser


def _read_json_file(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _coerce_synthetic_envelope(document: dict[str, Any]) -> dict[str, Any]:
    if document.get("ingestion_mode") is not None:
        if document.get("ingestion_mode") != "synthetic_test_only":
            raise ValueError(
                "ingest-synthetic accepts only raw exception-event payloads or "
                "synthetic_test_only envelopes."
            )
        return document
    return build_synthetic_envelope(document)


def _coerce_non_synthetic_preflight_envelope(document: dict[str, Any]) -> dict[str, Any]:
    if document.get("ingestion_mode") is not None:
        if document.get("ingestion_mode") != "non_synthetic_dry_run_preflight":
            raise ValueError(
                "non-synthetic-preflight accepts only readiness documents or "
                "non_synthetic_dry_run_preflight envelopes."
            )
        return document
    return build_non_synthetic_preflight_envelope(document)


def _refresh_contract_lock() -> dict[str, Any]:
    repo_root = Path(__file__).resolve().parents[2]
    script_path = repo_root / "scripts" / "update_contract_lock.py"
    subprocess.run(
        [sys.executable, str(script_path)],
        check=True,
        capture_output=True,
        text=True,
    )
    lock_path = repo_root / "contracts.lock.json"
    lock_document = json.loads(lock_path.read_text(encoding="utf-8"))
    return {
        "ok": True,
        "lock_path": str(lock_path),
        "locked_contract_sha": lock_document["contract_sha"],
        "non_production": True,
    }


def _emit_result(result: Any, exit_code: int | None = None) -> int:
    print(json.dumps(result, indent=2, sort_keys=True))
    if exit_code is not None:
        return exit_code

    if isinstance(result, dict):
        if result.get("ok") is False:
            return 1
        if result.get("mode") == "non_synthetic_dry_run_preflight":
            return 0 if result.get("preflight_ready") is True else 1
        if result.get("accepted") is False and result.get("stored") is False:
            return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
