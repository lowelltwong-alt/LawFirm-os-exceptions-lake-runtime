"""Synthetic replay descriptors for defect-class regression (PR-11)."""
from __future__ import annotations

from typing import Any

from exceptions_lake_runtime.eval_suites.registry import eval_suite_for_defect_class
from exceptions_lake_runtime.storage._json_store import content_hash
from exceptions_lake_runtime.substrate.reason_codes import is_registered_defect_class


def build_synthetic_replay_plan(
    defect: dict[str, Any],
    *,
    packet: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Representative replay plan for a defect (fixture-only; no live APIs)."""
    defect_class = defect["defect_class"]
    if not is_registered_defect_class(defect_class):
        raise ValueError(f"unregistered defect class: {defect_class}")

    plan: dict[str, Any] = {
        "schema_version": "eval_replay_plan.v1",
        "eval_suite": eval_suite_for_defect_class(defect_class),
        "defect_record_hash": defect["defect_record_hash"],
        "evidence_packet_hash": defect.get("evidence_packet_hash"),
        "contract_surface_sha256": defect.get("contract_surface_sha256"),
        "run_id": defect.get("run_id", ""),
        "replay_mode": "synthetic_fixture",
        "contains_production_data": False,
        "contains_client_data": False,
        "steps": [
            "load_synthetic_evidence_packet",
            "re_admit_via_central_admission",
            "assert_defect_or_quarantine_unchanged",
        ],
    }
    if packet:
        plan["context_bundle_ref"] = dict(packet.get("context_bundle_ref") or {})
        plan["execution_authority_record_count"] = len(packet.get("execution_authority_records") or [])
    plan["replay_plan_hash"] = content_hash(plan)
    return plan
