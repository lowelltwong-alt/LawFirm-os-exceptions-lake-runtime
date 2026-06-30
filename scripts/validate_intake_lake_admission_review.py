#!/usr/bin/env python3
"""Validate the candidate Exception Lake intake admission review docket."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
REGISTRY = ROOT / "registry" / "intake-lake-admission-review-registry.json"
EXPECTED_SOURCE_PROPOSAL_IDS = {
    "lake.intake-budget-evidence-mapping.v0_1",
    "lake.carrier-rejection-admission.v0_1",
}
REQUIRED_PROHIBITED_ACTIONS = {
    "canonical_route_id_creation",
    "canonical_event_class_creation",
    "semantic_substrate_write",
    "production_connector_write",
    "raw_legal_payload_storage",
    "real_data_ingestion",
    "sqlite_migration",
}
REQUIRED_ADMISSION_CONTROL_VALUES = {
    "append_only": True,
    "supersession_instead_of_update": True,
    "idempotency_key_required": True,
    "source_hash_required": True,
    "record_hash_required": True,
    "orchestrator_packet_required": True,
    "raw_payload_storage_allowed": False,
    "sqlite_migration_authorized_now": False,
    "real_data_authorized_now": False,
    "external_write_authorized_now": False,
}
REQUIRED_BUDGET_RECORD_FAMILIES = {
    "intake_proposal_packet",
    "intake_human_correction",
    "budget_template_mapping_report",
    "human_budget_change_record",
    "budget_revision_delta",
    "budget_actual_comparison",
    "budget_actual_variance_driver_candidate",
}
REQUIRED_CARRIER_RECORD_FAMILIES = {
    "carrier_rejection_notice",
    "carrier_rejection_reconciliation",
    "carrier_rejection_review_outcome",
    "carrier_appeal_submission",
    "carrier_appeal_result",
    "carrier_financial_outcome",
    "carrier_rejection_learning_candidate",
}
REQUIRED_CARRIER_BUCKETS = {
    "rate_or_cap_rejection",
    "staffing_or_leverage_rejection",
    "task_scope_rejection",
    "expense_documentation_rejection",
    "preapproval_missing",
    "duplicate_or_format_rejection",
    "timing_or_deadline_rejection",
    "portal_technical_rejection",
    "identity_or_matter_mismatch",
    "actuals_or_invoice_variance",
    "unknown_or_new_rejection_pattern",
}
REQUIRED_CARRIER_STATES = {
    "received_candidate",
    "reconciled_to_budget_or_invoice",
    "human_review_required",
    "appeal_authorized_by_human",
    "appeal_result_received",
    "closed_financial_outcome_recorded",
    "learning_candidate_prepared",
}
REQUIRED_ORCHESTRATOR_REVIEW_PACKET_CONTRACT = {
    "schema_version": "intake_lake_admission_review_packet.v0_1",
    "source_repo": "LawFirm-os-orchestrator",
    "target_repo": "LawFirm-os-exceptions-lake-runtime",
    "workflow_label": "orchestrator.local.intake_lake_admission_review_packet",
    "validation_script": "scripts/validate_intake_lake_admission_review_packet.py",
    "validation_report_schema_version": "intake_lake_admission_review_packet_validation_report.v0_1",
    "admission_allowed_now": False,
    "lake_write_authority_now": False,
    "sqlite_write_authorized_now": False,
    "raw_payload_storage_allowed": False,
    "real_data_authorized_now": False,
    "external_write_authorized_now": False,
    "canonical_route_id_assignment": "none",
    "canonical_event_class_assignment": "none",
    "candidate_review_only": True,
}


class IntakeLakeAdmissionReviewError(ValueError):
    """Raised when the candidate review docket violates evidence-plane boundaries."""


def _rel(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def _read_json(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise IntakeLakeAdmissionReviewError(f"{_rel(path)} unreadable: {exc}") from exc
    if not isinstance(data, dict):
        raise IntakeLakeAdmissionReviewError(f"{_rel(path)} must be a JSON object")
    return data


def _require_bool(data: dict[str, Any], key: str, expected: bool, label: str) -> None:
    if data.get(key) is not expected:
        raise IntakeLakeAdmissionReviewError(f"{label}.{key} must be {expected}")


def _require_string_list(data: dict[str, Any], key: str, label: str) -> list[str]:
    value = data.get(key)
    if not isinstance(value, list) or not value:
        raise IntakeLakeAdmissionReviewError(f"{label}.{key} must be a non-empty list")
    if not all(isinstance(item, str) and item.strip() for item in value):
        raise IntakeLakeAdmissionReviewError(
            f"{label}.{key} must contain only non-empty strings"
        )
    return value


def _validate_top_level(data: dict[str, Any], label: str) -> None:
    expected = {
        "schema_version": "intake_lake_admission_review_registry.v0_1",
        "object_type": "intake_lake_admission_review_registry",
        "status": "candidate_review_only",
        "owner_repo": "LawFirm-os-exceptions-lake-runtime",
        "source_repo": "LawFirm-os-intake",
    }
    for key, value in expected.items():
        if data.get(key) != value:
            raise IntakeLakeAdmissionReviewError(f"{label}.{key} must be {value!r}")

    for key in (
        "contains_real_firm_data",
        "direct_promotion_performed",
        "external_writes_performed",
        "canonical_route_ids_assigned",
        "canonical_event_classes_assigned",
        "sqlite_migrations_authorized",
        "runtime_connector_authorized",
        "raw_legal_payload_storage_authorized",
        "real_data_pilot_authorized",
    ):
        _require_bool(data, key, False, label)
    _require_bool(data, "non_authoritative", True, label)

    generated = set(_require_string_list(data, "generated_from_proposal_ids", label))
    if generated != EXPECTED_SOURCE_PROPOSAL_IDS:
        raise IntakeLakeAdmissionReviewError(
            f"{label}.generated_from_proposal_ids must be {sorted(EXPECTED_SOURCE_PROPOSAL_IDS)}"
        )


def _validate_admission_controls(item: dict[str, Any], label: str) -> None:
    controls = item.get("required_admission_controls")
    if not isinstance(controls, dict):
        raise IntakeLakeAdmissionReviewError(
            f"{label}.required_admission_controls must be an object"
        )
    for key, expected in REQUIRED_ADMISSION_CONTROL_VALUES.items():
        if controls.get(key) is not expected:
            raise IntakeLakeAdmissionReviewError(
                f"{label}.required_admission_controls.{key} must be {expected}"
            )


def _validate_event_mapping_policy(item: dict[str, Any], label: str) -> None:
    policy = item.get("event_mapping_policy")
    if not isinstance(policy, dict):
        raise IntakeLakeAdmissionReviewError(
            f"{label}.event_mapping_policy must be an object"
        )
    if policy.get("canonical_route_id_assignment") != "none":
        raise IntakeLakeAdmissionReviewError(
            f"{label} must not assign canonical route_id"
        )
    if policy.get("canonical_event_class_assignment") != "none":
        raise IntakeLakeAdmissionReviewError(
            f"{label} must not assign canonical event_class"
        )
    if policy.get("candidate_mapping_only") is not True:
        raise IntakeLakeAdmissionReviewError(
            f"{label}.event_mapping_policy must stay candidate-only"
        )


def _validate_common_item(item: dict[str, Any], label: str) -> None:
    if item.get("target_repo") != "LawFirm-os-exceptions-lake-runtime":
        raise IntakeLakeAdmissionReviewError(
            f"{label}.target_repo must be Exception Lake"
        )
    if item.get("authority_plane") != "evidence":
        raise IntakeLakeAdmissionReviewError(
            f"{label}.authority_plane must be evidence"
        )
    if item.get("adoption_status") != "owner_review_required":
        raise IntakeLakeAdmissionReviewError(
            f"{label}.adoption_status must be owner_review_required"
        )
    local_label = item.get("local_admission_label")
    if not isinstance(local_label, str) or not local_label.startswith(
        "exception_lake.local."
    ):
        raise IntakeLakeAdmissionReviewError(
            f"{label}.local_admission_label must be local-only"
        )
    proposed_refs = _require_string_list(item, "proposed_contract_refs", label)
    invalid_refs = [
        ref
        for ref in proposed_refs
        if not ref.startswith("exception-lake://candidate/")
    ]
    if invalid_refs:
        raise IntakeLakeAdmissionReviewError(
            f"{label}.proposed_contract_refs must stay candidate-only: {invalid_refs}"
        )

    prohibited = set(_require_string_list(item, "prohibited_actions", label))
    missing = sorted(REQUIRED_PROHIBITED_ACTIONS - prohibited)
    if missing:
        raise IntakeLakeAdmissionReviewError(
            f"{label}.prohibited_actions missing {missing}"
        )

    _require_bool(item, "non_authoritative", True, label)
    _require_bool(item, "direct_promotion_performed", False, label)
    _require_bool(item, "external_writes_performed", False, label)
    _validate_admission_controls(item, label)
    _validate_event_mapping_policy(item, label)


def _validate_budget_item(item: dict[str, Any], label: str) -> None:
    families = set(_require_string_list(item, "candidate_record_families", label))
    missing = sorted(REQUIRED_BUDGET_RECORD_FAMILIES - families)
    if missing:
        raise IntakeLakeAdmissionReviewError(
            f"{label}.candidate_record_families missing {missing}"
        )

    handoff = set(_require_string_list(item, "required_handoff_fields", label))
    for required in ("orchestrator_evidence_packet_hash", "source_hash", "record_hash"):
        if required not in handoff:
            raise IntakeLakeAdmissionReviewError(
                f"{label}.required_handoff_fields missing {required}"
            )

    actuals = set(_require_string_list(item, "budget_actuals_comparison_fields", label))
    required_actuals = {
        "proposed_budget_amount",
        "carrier_compliant_projection_amount",
        "approved_budget_amount_if_known",
        "actual_billed_amount",
        "write_down_or_disallowed_amount",
        "variance_driver_candidate",
    }
    missing_actuals = sorted(required_actuals - actuals)
    if missing_actuals:
        raise IntakeLakeAdmissionReviewError(
            f"{label}.budget_actuals_comparison_fields missing {missing_actuals}"
        )


def _validate_carrier_item(item: dict[str, Any], label: str) -> None:
    families = set(_require_string_list(item, "candidate_record_families", label))
    missing = sorted(REQUIRED_CARRIER_RECORD_FAMILIES - families)
    if missing:
        raise IntakeLakeAdmissionReviewError(
            f"{label}.candidate_record_families missing {missing}"
        )

    sources = item.get("future_capture_sources")
    if not isinstance(sources, list) or not sources:
        raise IntakeLakeAdmissionReviewError(f"{label}.future_capture_sources missing")
    source_names = {entry.get("source") for entry in sources if isinstance(entry, dict)}
    if source_names != {"email", "carrier_portal"}:
        raise IntakeLakeAdmissionReviewError(
            f"{label}.future_capture_sources must include email and carrier_portal"
        )
    if any(
        entry.get("enabled_now") is not False
        for entry in sources
        if isinstance(entry, dict)
    ):
        raise IntakeLakeAdmissionReviewError(
            f"{label}.future_capture_sources must remain disabled now"
        )

    buckets = set(_require_string_list(item, "candidate_rejection_buckets", label))
    missing_buckets = sorted(REQUIRED_CARRIER_BUCKETS - buckets)
    if missing_buckets:
        raise IntakeLakeAdmissionReviewError(
            f"{label}.candidate_rejection_buckets missing {missing_buckets}"
        )

    states = set(_require_string_list(item, "required_state_chain", label))
    missing_states = sorted(REQUIRED_CARRIER_STATES - states)
    if missing_states:
        raise IntakeLakeAdmissionReviewError(
            f"{label}.required_state_chain missing {missing_states}"
        )

    learning_inputs = set(_require_string_list(item, "learning_loop_inputs", label))
    if "new_rejection_pattern_candidate" not in learning_inputs:
        raise IntakeLakeAdmissionReviewError(
            f"{label}.learning_loop_inputs must include new_rejection_pattern_candidate"
        )
    controls = item["required_admission_controls"]
    if controls.get("unknown_bucket_required") is not True:
        raise IntakeLakeAdmissionReviewError(
            f"{label}.required_admission_controls.unknown_bucket_required must be true"
        )


def _validate_orchestrator_packet_contract(data: dict[str, Any], label: str) -> None:
    contract = data.get("orchestrator_review_packet_contract")
    if not isinstance(contract, dict):
        raise IntakeLakeAdmissionReviewError(
            f"{label}.orchestrator_review_packet_contract must be an object"
        )
    for key, expected in REQUIRED_ORCHESTRATOR_REVIEW_PACKET_CONTRACT.items():
        if contract.get(key) != expected:
            raise IntakeLakeAdmissionReviewError(
                f"{label}.orchestrator_review_packet_contract.{key} must be {expected!r}"
            )
    validation_script = ROOT / contract["validation_script"]
    if not validation_script.exists():
        raise IntakeLakeAdmissionReviewError(
            f"{label}.orchestrator_review_packet_contract.validation_script missing"
        )


def validate_intake_lake_admission_review(path: Path = REGISTRY) -> dict[str, Any]:
    data = _read_json(path)
    label = _rel(path)
    _validate_top_level(data, label)
    _validate_orchestrator_packet_contract(data, label)

    items = data.get("review_items")
    if not isinstance(items, list) or len(items) != len(EXPECTED_SOURCE_PROPOSAL_IDS):
        raise IntakeLakeAdmissionReviewError(
            f"{label}.review_items must contain exactly {len(EXPECTED_SOURCE_PROPOSAL_IDS)} items"
        )

    seen = set()
    for index, item in enumerate(items):
        if not isinstance(item, dict):
            raise IntakeLakeAdmissionReviewError(
                f"{label}.review_items[{index}] must be an object"
            )
        item_label = f"{label}.review_items[{index}]"
        proposal_id = item.get("source_proposal_id")
        if proposal_id not in EXPECTED_SOURCE_PROPOSAL_IDS:
            raise IntakeLakeAdmissionReviewError(
                f"{item_label}.source_proposal_id is not expected: {proposal_id!r}"
            )
        seen.add(proposal_id)
        _validate_common_item(item, item_label)
        if proposal_id == "lake.intake-budget-evidence-mapping.v0_1":
            _validate_budget_item(item, item_label)
        elif proposal_id == "lake.carrier-rejection-admission.v0_1":
            _validate_carrier_item(item, item_label)

    if seen != EXPECTED_SOURCE_PROPOSAL_IDS:
        raise IntakeLakeAdmissionReviewError(
            f"{label}.review_items missing {sorted(EXPECTED_SOURCE_PROPOSAL_IDS - seen)}"
        )
    return data


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--registry", type=Path, default=REGISTRY)
    args = parser.parse_args(argv)

    try:
        validate_intake_lake_admission_review(args.registry)
    except IntakeLakeAdmissionReviewError as exc:
        print(f"Intake Lake admission review validation failed: {exc}", file=sys.stderr)
        return 1
    print("Intake Lake admission review validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
