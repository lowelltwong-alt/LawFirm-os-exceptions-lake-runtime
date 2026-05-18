from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from exceptions_lake_runtime.storage._json_store import content_hash
from exceptions_lake_runtime.substrate.reason_codes import is_registered_defect_class


SCHEMA_VERSION = "eval_candidate.v1"
ELIGIBLE_SEVERITIES = frozenset({"high", "critical"})


def _iso_utc_now() -> str:
    return datetime.now(tz=UTC).isoformat().replace("+00:00", "Z")


def generate_eval_candidate_from_defect(
    defect: dict[str, Any],
    *,
    generated_at: str | None = None,
) -> dict[str, Any] | None:
    if defect.get("severity") not in ELIGIBLE_SEVERITIES:
        return None
    defect_class = defect["defect_class"]
    if not is_registered_defect_class(defect_class):
        raise ValueError(f"unregistered defect class: {defect_class}")
    record: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "eval_candidate_id": f"eval-{defect['defect_record_hash'][:16]}",
        "contract_surface_sha256": defect["contract_surface_sha256"],
        "source_defect_record_hash": defect["defect_record_hash"],
        "evidence_packet_hash": defect.get("evidence_packet_hash"),
        "eval_class": defect_class,
        "suggested_test_steps": [
            {
                "step_id": "replay-defect-evidence",
                "step_description_hash": content_hash({"step": "Replay the evidence packet that produced this defect."}),
            },
            {
                "step_id": "assert-no-canon-mutation",
                "step_description_hash": content_hash({"step": "Assert the proposal path does not mutate substrate canon."}),
            },
        ],
        "generated_at": generated_at or _iso_utc_now(),
        "source_repo": "LawFirm-os-exceptions-lake-runtime-main",
        "promotion_status": "candidate",
    }
    record["eval_candidate_hash"] = content_hash(record)
    return record

