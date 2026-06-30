from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from exceptions_lake_runtime.storage._json_store import content_hash


PACKET_SCHEMA_VERSION = "intake_lake_admission_review_packet.v0_1"
REPORT_SCHEMA_VERSION = "intake_lake_admission_review_packet_validation_report.v0_1"
WORKFLOW_LABEL = "orchestrator.local.intake_lake_admission_review_packet"
OWNER_WORKFLOW_LABEL = "orchestrator.local.intake_to_budget_owner_review"
EXPECTED_STATUS = "blocked_pending_exception_lake_owner_review"
EXPECTED_SOURCE_REPO = "LawFirm-os-orchestrator"
EXPECTED_SOURCE_VERTICAL_REPO = "LawFirm-os-intake"
EXPECTED_TARGET_REPO = "LawFirm-os-exceptions-lake-runtime"
VALID_SHA256 = re.compile(r"^[0-9a-f]{64}$")

RAW_OR_REAL_DATA_KEYS = {
    "raw_client_payload",
    "raw_matter_payload",
    "raw_legal_payload",
    "raw_notice_payload",
    "raw_email_body",
    "raw_portal_download",
    "privileged_text",
    "real_client_name",
    "real_matter_number",
    "client_secret",
    "production_transcript",
}

REQUIRED_PROHIBITED_ACTIONS = {
    "write_exception_lake_record",
    "write_sqlite_exception_lake",
    "store_raw_legal_payload",
    "ingest_real_data",
    "submit_budget_to_client_or_carrier",
    "submit_appeal_without_human_authorization",
    "create_canonical_route_id",
    "create_canonical_event_class",
    "write_semantic_substrate",
}

REQUIRED_ADMISSION_CONTROLS = {
    "append_only_required": True,
    "supersession_instead_of_update_required": True,
    "idempotency_key_required": True,
    "source_hash_required": True,
    "record_hash_required_before_admission": True,
    "orchestrator_packet_required": True,
    "raw_payload_storage_allowed": False,
    "sqlite_write_authorized_now": False,
    "real_data_authorized_now": False,
    "external_write_authorized_now": False,
    "lake_write_authority_now": False,
    "lake_handoff_allowed": False,
    "canonical_route_id_assignment": "none",
    "canonical_event_class_assignment": "none",
}

LOCAL_ALLOWED_FALLBACK_FAMILIES = {
    "intake_proposal_packet",
    "intake_human_correction",
    "intake_escalation_or_blocker",
    "budget_template_mapping_report",
    "human_budget_change_record",
    "budget_revision_delta",
    "budget_actual_comparison",
    "budget_actual_variance_driver_candidate",
    "reviewed_learning_gate_candidate",
    "carrier_rejection_notice",
    "carrier_rejection_reconciliation",
    "carrier_rejection_review_outcome",
    "carrier_fix_or_appeal_action",
    "carrier_appeal_submission",
    "carrier_appeal_result",
    "carrier_financial_outcome",
    "carrier_rejection_learning_candidate",
}


class IntakeLakeAdmissionReviewPacketError(ValueError):
    """Raised when an Orchestrator intake Lake-review packet is unsafe."""


def _read_json(path: Path) -> dict[str, Any]:
    import json

    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise IntakeLakeAdmissionReviewPacketError(f"{path} must be a JSON object")
    return data


def _require_mapping(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise IntakeLakeAdmissionReviewPacketError(f"{label} must be an object")
    return value


def _require_list(value: Any, label: str) -> list[Any]:
    if not isinstance(value, list):
        raise IntakeLakeAdmissionReviewPacketError(f"{label} must be a list")
    return value


def _require_bool(data: dict[str, Any], key: str, expected: bool, label: str) -> None:
    if data.get(key) is not expected:
        raise IntakeLakeAdmissionReviewPacketError(f"{label}.{key} must be {expected}")


def _contains_forbidden_key(value: Any, path: str = "$") -> str | None:
    if isinstance(value, dict):
        for key, child in value.items():
            if key in RAW_OR_REAL_DATA_KEYS:
                return f"{path}.{key}"
            found = _contains_forbidden_key(child, f"{path}.{key}")
            if found:
                return found
    elif isinstance(value, list):
        for index, child in enumerate(value):
            found = _contains_forbidden_key(child, f"{path}[{index}]")
            if found:
                return found
    return None


def _hash_without_field(payload: dict[str, Any], field: str) -> str:
    clean = {key: value for key, value in payload.items() if key != field}
    return content_hash(clean)


def _load_allowed_record_families(registry_path: Path | None) -> set[str]:
    if registry_path is None:
        return set(LOCAL_ALLOWED_FALLBACK_FAMILIES)
    registry = _read_json(registry_path)
    families: set[str] = set()
    for raw_item in registry.get("review_items", []):
        if not isinstance(raw_item, dict):
            continue
        for family in raw_item.get("candidate_record_families", []):
            if isinstance(family, str) and family.strip():
                families.add(family)
    return families or set(LOCAL_ALLOWED_FALLBACK_FAMILIES)


def _validate_top_level(packet: dict[str, Any]) -> None:
    expected_values = {
        "schema_version": PACKET_SCHEMA_VERSION,
        "source_repo": EXPECTED_SOURCE_REPO,
        "source_vertical_repo": EXPECTED_SOURCE_VERTICAL_REPO,
        "target_repo": EXPECTED_TARGET_REPO,
        "workflow_label": WORKFLOW_LABEL,
        "owner_workflow_label": OWNER_WORKFLOW_LABEL,
        "status": EXPECTED_STATUS,
    }
    for key, expected in expected_values.items():
        if packet.get(key) != expected:
            raise IntakeLakeAdmissionReviewPacketError(
                f"packet.{key} must be {expected!r}"
            )

    for key in (
        "owner_packet_id",
        "owner_packet_hash",
        "owner_packet_status",
        "packet_id",
        "packet_hash",
    ):
        if not str(packet.get(key, "")).strip():
            raise IntakeLakeAdmissionReviewPacketError(f"packet.{key} is required")

    _require_bool(packet, "synthetic", True, "packet")
    _require_bool(packet, "contains_real_firm_data", False, "packet")
    for flag in (
        "contains_real_client_data",
        "contains_real_matter_data",
        "contains_privileged_data",
    ):
        if packet.get(flag) is True:
            raise IntakeLakeAdmissionReviewPacketError(f"packet.{flag} must be false")
    _require_bool(packet, "non_authoritative", True, "packet")
    _require_bool(packet, "proposed_for_owner_review", True, "packet")
    _require_bool(packet, "not_authorized_for_client_submission", True, "packet")

    if not VALID_SHA256.match(str(packet["packet_hash"])):
        raise IntakeLakeAdmissionReviewPacketError("packet.packet_hash must be sha256")
    if not VALID_SHA256.match(str(packet["owner_packet_hash"])):
        raise IntakeLakeAdmissionReviewPacketError(
            "packet.owner_packet_hash must be sha256"
        )
    observed = _hash_without_field(packet, "packet_hash")
    if observed != packet["packet_hash"]:
        raise IntakeLakeAdmissionReviewPacketError(
            "packet.packet_hash does not match canonical content"
        )


def _validate_admission_controls(packet: dict[str, Any]) -> None:
    controls = _require_mapping(packet.get("admission_controls"), "admission_controls")
    for key, expected in REQUIRED_ADMISSION_CONTROLS.items():
        if controls.get(key) != expected:
            raise IntakeLakeAdmissionReviewPacketError(
                f"admission_controls.{key} must be {expected!r}"
            )


def _validate_source_inventory(packet: dict[str, Any]) -> None:
    summary = _require_mapping(
        packet.get("source_inventory_summary"), "source_inventory_summary"
    )
    source_hashes = _require_list(
        summary.get("source_hashes", []), "source_inventory_summary.source_hashes"
    )
    for source_hash in source_hashes:
        if not isinstance(source_hash, str) or not VALID_SHA256.match(source_hash):
            raise IntakeLakeAdmissionReviewPacketError(
                "source_inventory_summary.source_hashes must be sha256 values"
            )
    invalid_hash_values = summary.get("invalid_hash_values_detected", [])
    if invalid_hash_values:
        raise IntakeLakeAdmissionReviewPacketError(
            "source_inventory_summary must not contain invalid hash values"
        )


def _validate_candidate_record(
    record: dict[str, Any],
    *,
    allowed_families: set[str],
    index: int,
) -> str:
    label = f"candidate_record_summaries[{index}]"
    family = str(record.get("record_family", "")).strip()
    if family not in allowed_families:
        raise IntakeLakeAdmissionReviewPacketError(
            f"{label}.record_family is not allowed: {family!r}"
        )
    if not str(record.get("local_record_label", "")).strip():
        raise IntakeLakeAdmissionReviewPacketError(
            f"{label}.local_record_label is required"
        )
    proposed_ref = str(record.get("proposed_contract_ref", "")).strip()
    if not proposed_ref.startswith("exception-lake://candidate/"):
        raise IntakeLakeAdmissionReviewPacketError(
            f"{label}.proposed_contract_ref must stay candidate-only"
        )
    _require_bool(record, "candidate_only", True, label)
    _require_bool(record, "owner_review_required", True, label)
    if record.get("admission_status") != "not_admitted":
        raise IntakeLakeAdmissionReviewPacketError(
            f"{label}.admission_status must be not_admitted"
        )
    _require_bool(record, "record_hash_required_before_admission", True, label)
    if record.get("record_hash_status") != (
        "not_minted_until_exception_lake_owner_contract_acceptance"
    ):
        raise IntakeLakeAdmissionReviewPacketError(
            f"{label}.record_hash_status must block record hash minting"
        )
    if record.get("contract_surface_sha256") is not None:
        raise IntakeLakeAdmissionReviewPacketError(
            f"{label}.contract_surface_sha256 must be null until owner acceptance"
        )
    if record.get("previous_record_hash_or_null") is not None:
        raise IntakeLakeAdmissionReviewPacketError(
            f"{label}.previous_record_hash_or_null must be null for candidate packet"
        )
    if not VALID_SHA256.match(str(record.get("idempotency_key", ""))):
        raise IntakeLakeAdmissionReviewPacketError(
            f"{label}.idempotency_key must be sha256"
        )
    for source_hash in record.get("source_hashes", []):
        if not isinstance(source_hash, str) or not VALID_SHA256.match(source_hash):
            raise IntakeLakeAdmissionReviewPacketError(
                f"{label}.source_hashes must contain sha256 values"
            )
    declared = str(record.get("candidate_record_summary_hash", "")).strip()
    if not VALID_SHA256.match(declared):
        raise IntakeLakeAdmissionReviewPacketError(
            f"{label}.candidate_record_summary_hash must be sha256"
        )
    observed = _hash_without_field(record, "candidate_record_summary_hash")
    if observed != declared:
        raise IntakeLakeAdmissionReviewPacketError(
            f"{label}.candidate_record_summary_hash does not match canonical content"
        )
    if not isinstance(record.get("blockers", []), list):
        raise IntakeLakeAdmissionReviewPacketError(f"{label}.blockers must be a list")
    return family


def _validate_candidate_records(
    packet: dict[str, Any], *, allowed_families: set[str]
) -> list[str]:
    records = _require_list(
        packet.get("candidate_record_summaries", []), "candidate_record_summaries"
    )
    if not records:
        raise IntakeLakeAdmissionReviewPacketError(
            "candidate_record_summaries must not be empty"
        )
    if packet.get("candidate_record_count") != len(records):
        raise IntakeLakeAdmissionReviewPacketError(
            "candidate_record_count must equal candidate_record_summaries length"
        )
    observed_families = [
        _validate_candidate_record(
            _require_mapping(record, "candidate_record_summaries[]"),
            allowed_families=allowed_families,
            index=index,
        )
        for index, record in enumerate(records)
    ]
    declared_families = packet.get("candidate_admission_record_families")
    if not isinstance(declared_families, list) or not declared_families:
        raise IntakeLakeAdmissionReviewPacketError(
            "candidate_admission_record_families must be a non-empty list"
        )
    if sorted(set(observed_families)) != sorted(set(declared_families)):
        raise IntakeLakeAdmissionReviewPacketError(
            "candidate_admission_record_families must match record summaries"
        )
    return sorted(set(observed_families))


def validate_intake_lake_admission_review_packet(
    packet: dict[str, Any],
    *,
    registry_path: Path | None = None,
) -> dict[str, Any]:
    """Validate an Orchestrator intake Lake-review packet without admitting it."""

    forbidden = _contains_forbidden_key(packet)
    if forbidden:
        raise IntakeLakeAdmissionReviewPacketError(
            f"forbidden raw/real data field is not allowed: {forbidden}"
        )

    _validate_top_level(packet)
    _validate_admission_controls(packet)
    _validate_source_inventory(packet)

    prohibited = set(
        _require_list(packet.get("prohibited_actions", []), "prohibited_actions")
    )
    missing_prohibited = sorted(REQUIRED_PROHIBITED_ACTIONS - prohibited)
    if missing_prohibited:
        raise IntakeLakeAdmissionReviewPacketError(
            f"prohibited_actions missing {missing_prohibited}"
        )

    allowed_families = _load_allowed_record_families(registry_path)
    record_families = _validate_candidate_records(
        packet, allowed_families=allowed_families
    )
    blockers = _require_list(packet.get("blockers", []), "blockers")
    if "exception_lake_owner_contract:required" not in blockers:
        raise IntakeLakeAdmissionReviewPacketError(
            "blockers must include exception_lake_owner_contract:required"
        )

    report: dict[str, Any] = {
        "schema_version": REPORT_SCHEMA_VERSION,
        "status": "passed_candidate_packet_validation",
        "packet_id": packet["packet_id"],
        "packet_hash": packet["packet_hash"],
        "owner_packet_id": packet["owner_packet_id"],
        "owner_packet_hash": packet["owner_packet_hash"],
        "source_repo": EXPECTED_SOURCE_REPO,
        "target_repo": EXPECTED_TARGET_REPO,
        "synthetic": True,
        "non_authoritative": True,
        "not_authorized_for_client_submission": True,
        "admission_allowed_now": False,
        "lake_write_authority_now": False,
        "sqlite_write_authorized_now": False,
        "raw_payload_storage_allowed": False,
        "canonical_route_id_assignment": "none",
        "canonical_event_class_assignment": "none",
        "candidate_record_count": packet["candidate_record_count"],
        "candidate_record_families": record_families,
        "blocker_count": len(blockers),
        "validation_notes": [
            "packet_valid_for_owner_review_only",
            "no_exception_lake_admission_performed",
            "no_sqlite_or_external_write_authorized",
        ],
    }
    report["validation_report_hash"] = content_hash(report)
    return report
