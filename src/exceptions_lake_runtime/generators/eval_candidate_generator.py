from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from exceptions_lake_runtime.eval_suites.registry import eval_suite_for_defect_class
from exceptions_lake_runtime.generators.acceptance_test_generator import generate_acceptance_test_steps
from exceptions_lake_runtime.generators.eval_replay import build_synthetic_replay_plan
from exceptions_lake_runtime.storage._json_store import content_hash
from exceptions_lake_runtime.substrate.reason_codes import is_registered_defect_class


SCHEMA_VERSION = "eval_candidate.v1"
ELIGIBLE_SEVERITIES = frozenset({"high", "critical"})


def _iso_utc_now() -> str:
    return datetime.now(tz=UTC).isoformat().replace("+00:00", "Z")


def generate_eval_candidate_from_defect(
    defect: dict[str, Any],
    *,
    packet: dict[str, Any] | None = None,
    generated_at: str | None = None,
) -> dict[str, Any] | None:
    if defect.get("severity") not in ELIGIBLE_SEVERITIES:
        return None
    defect_class = defect["defect_class"]
    if not is_registered_defect_class(defect_class):
        raise ValueError(f"unregistered defect class: {defect_class}")

    eval_class = eval_suite_for_defect_class(defect_class)
    evidence_hash = defect.get("evidence_packet_hash") or (packet or {}).get("evidence_packet_hash")
    steps = generate_acceptance_test_steps(defect, packet=packet)
    replay = build_synthetic_replay_plan(defect, packet=packet)

    record: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "eval_candidate_id": f"eval-{defect['defect_record_hash'][:16]}",
        "contract_surface_sha256": defect["contract_surface_sha256"],
        "source_defect_record_hash": defect["defect_record_hash"],
        "evidence_packet_hash": evidence_hash,
        "eval_class": eval_class,
        "suggested_test_steps": steps,
        "generated_at": generated_at or _iso_utc_now(),
        "source_repo": "LawFirm-os-exceptions-lake-runtime-main",
        "promotion_status": "candidate",
    }
    # Replay descriptor is stored as a hashed sidecar step (proposal-only; not canon).
    record["suggested_test_steps"].append(
        {
            "step_id": "synthetic-replay-plan",
            "step_description_hash": content_hash({"replay_plan": replay}),
        }
    )
    record["eval_candidate_hash"] = content_hash(record)
    return record
