#!/usr/bin/env python3
"""Validate an Orchestrator intake Lake admission-review packet."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC_ROOT = ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from exceptions_lake_runtime.intake_lake_admission_review_packet import (  # noqa: E402
    IntakeLakeAdmissionReviewPacketError,
    validate_intake_lake_admission_review_packet,
)


DEFAULT_REGISTRY = ROOT / "registry" / "intake-lake-admission-review-registry.json"


def _read_json(path: Path) -> dict:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise IntakeLakeAdmissionReviewPacketError(f"{path} must be a JSON object")
    return data


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--packet", type=Path, required=True)
    parser.add_argument("--registry", type=Path, default=DEFAULT_REGISTRY)
    parser.add_argument("--report-out", type=Path)
    parser.add_argument("--stdout", choices=["json", "text"], default="text")
    args = parser.parse_args(argv)

    try:
        packet = _read_json(args.packet)
        report = validate_intake_lake_admission_review_packet(
            packet,
            registry_path=args.registry,
        )
        if args.report_out:
            args.report_out.parent.mkdir(parents=True, exist_ok=True)
            args.report_out.write_text(
                json.dumps(report, indent=2, sort_keys=False) + "\n",
                encoding="utf-8",
            )
    except (OSError, json.JSONDecodeError, IntakeLakeAdmissionReviewPacketError) as exc:
        print(
            f"Intake Lake admission-review packet validation failed: {exc}",
            file=sys.stderr,
        )
        return 1

    if args.stdout == "json":
        print(json.dumps(report, indent=2, sort_keys=False))
    else:
        print("Intake Lake admission-review packet validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
