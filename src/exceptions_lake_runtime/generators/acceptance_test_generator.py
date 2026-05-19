"""Acceptance-test step generation for defect-class eval suites (PR-11)."""
from __future__ import annotations

from typing import Any

from exceptions_lake_runtime.eval_suites.registry import suite_step_templates
from exceptions_lake_runtime.storage._json_store import content_hash
from exceptions_lake_runtime.substrate.reason_codes import is_registered_defect_class


def generate_acceptance_test_steps(
    defect: dict[str, Any],
    *,
    packet: dict[str, Any] | None = None,
) -> list[dict[str, str]]:
    """Build hash-only acceptance test steps for a defect (no raw privileged payloads)."""
    defect_class = defect["defect_class"]
    if not is_registered_defect_class(defect_class):
        raise ValueError(f"unregistered defect class: {defect_class}")

    steps: list[dict[str, str]] = []
    for step_id, description in suite_step_templates(defect_class):
        steps.append(
            {
                "step_id": step_id,
                "step_description_hash": content_hash(
                    {
                        "step_id": step_id,
                        "defect_class": defect_class,
                        "description": description,
                        "evidence_packet_hash": defect.get("evidence_packet_hash"),
                    }
                ),
            }
        )

    if packet:
        steps.append(
            {
                "step_id": "link-evidence-packet-hash",
                "step_description_hash": content_hash(
                    {
                        "step": "Bind regression replay to evidence_packet_hash.",
                        "evidence_packet_hash": packet.get("evidence_packet_hash"),
                    }
                ),
            }
        )
        if packet.get("source_refs"):
            steps.append(
                {
                    "step_id": "link-source-refs",
                    "step_description_hash": content_hash(
                        {"source_ref_ids": [r.get("source_ref_id") for r in packet["source_refs"]]}
                    ),
                }
            )
        claim_ids = [r.get("claim_ref_id") for r in packet.get("claim_refs") or [] if r.get("claim_ref_id")]
        if claim_ids:
            steps.append(
                {
                    "step_id": "link-claim-refs",
                    "step_description_hash": content_hash({"claim_ref_ids": claim_ids}),
                }
            )

    return steps
