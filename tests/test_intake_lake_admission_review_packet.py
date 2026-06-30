from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from exceptions_lake_runtime.intake_lake_admission_review_packet import (
    IntakeLakeAdmissionReviewPacketError,
    validate_intake_lake_admission_review_packet,
)
from exceptions_lake_runtime.storage._json_store import content_hash


ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "registry" / "intake-lake-admission-review-registry.json"
VALIDATOR = ROOT / "scripts" / "validate_intake_lake_admission_review_packet.py"
SOURCE_HASH = "a" * 64


def _rehash_record(record: dict) -> dict:
    clean = {
        key: value
        for key, value in record.items()
        if key != "candidate_record_summary_hash"
    }
    record["candidate_record_summary_hash"] = content_hash(clean)
    return record


def _record(family: str, label: str) -> dict:
    return _rehash_record(
        {
            "record_family": family,
            "local_record_label": label,
            "proposed_contract_ref": (
                "exception-lake://candidate/admission/carrier-rejection-notice.v0_1"
                if family.startswith("carrier_")
                else "exception-lake://candidate/evidence/intake-proposal-correction-escalation.v0_1"
            ),
            "candidate_only": True,
            "owner_review_required": True,
            "admission_status": "not_admitted",
            "source_ref_ids": ["source-1"],
            "source_hashes": [SOURCE_HASH],
            "source_hash_status": "present",
            "evidence_ref": f"evidence:{family}",
            "idempotency_key": content_hash({"family": family, "label": label}),
            "record_hash_required_before_admission": True,
            "record_hash_status": "not_minted_until_exception_lake_owner_contract_acceptance",
            "previous_record_hash_or_null": None,
            "contract_surface_sha256": None,
            "detail": {"family": family},
            "blockers": [],
        }
    )


def _packet() -> dict:
    records = [
        _record("intake_proposal_packet", "owner_review_packet_summary"),
        _record("budget_actual_comparison", "budget_actuals_summary"),
        _record("carrier_rejection_notice", "carrier_notice_candidate"),
    ]
    families = sorted({record["record_family"] for record in records})
    packet = {
        "schema_version": "intake_lake_admission_review_packet.v0_1",
        "packet_id": "intake_lake_review_test",
        "generated_at": "2026-06-30T00:00:00Z",
        "source_repo": "LawFirm-os-orchestrator",
        "source_vertical_repo": "LawFirm-os-intake",
        "target_repo": "LawFirm-os-exceptions-lake-runtime",
        "workflow_label": "orchestrator.local.intake_lake_admission_review_packet",
        "owner_workflow_label": "orchestrator.local.intake_to_budget_owner_review",
        "owner_packet_id": "intake_owner_packet_test",
        "owner_packet_hash": "b" * 64,
        "owner_packet_status": "blocked_pending_owner_review",
        "request_id": "synthetic-request",
        "synthetic": True,
        "contains_real_firm_data": False,
        "non_authoritative": True,
        "proposed_for_owner_review": True,
        "not_authorized_for_client_submission": True,
        "status": "blocked_pending_exception_lake_owner_review",
        "admission_controls": {
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
        },
        "idempotency_basis": {
            "owner_packet_id": "intake_owner_packet_test",
            "owner_packet_hash": "b" * 64,
            "request_id": "synthetic-request",
            "workflow_label": "orchestrator.local.intake_to_budget_owner_review",
            "source_ref_ids": ["source-1"],
            "source_hashes": [SOURCE_HASH],
        },
        "source_inventory_summary": {
            "status": "passed",
            "source_count": 1,
            "source_ref_ids": ["source-1"],
            "source_hashes": [SOURCE_HASH],
            "duplicate_source_ref_ids": [],
            "duplicate_hashes": [],
            "missing_hash_source_ref_ids": [],
            "invalid_hash_source_ref_ids": [],
            "invalid_hash_values_detected": [],
        },
        "owner_review_gate_summary": {
            "human_pause_status": "blocked",
            "budget_precondition_status": "blocked",
            "carrier_rejection_status": "passed",
            "budget_actuals_status": "passed",
            "decision_model_status": "missing_promoted_intake_to_budget_decision_model",
            "owner_blockers": ["decision_model:missing"],
        },
        "candidate_admission_record_families": families,
        "candidate_record_count": len(records),
        "candidate_record_summaries": records,
        "required_owner_decisions": [
            "exception_lake_owner_accepts_or_rejects_candidate_record_families"
        ],
        "prohibited_actions": [
            "write_exception_lake_record",
            "write_sqlite_exception_lake",
            "store_raw_legal_payload",
            "ingest_real_data",
            "submit_budget_to_client_or_carrier",
            "submit_appeal_without_human_authorization",
            "create_canonical_route_id",
            "create_canonical_event_class",
            "write_semantic_substrate",
        ],
        "blockers": ["exception_lake_owner_contract:required"],
    }
    packet["packet_hash"] = content_hash(packet)
    return packet


def _rehash_packet(packet: dict) -> dict:
    clean = {key: value for key, value in packet.items() if key != "packet_hash"}
    packet["packet_hash"] = content_hash(clean)
    return packet


def test_orchestrator_intake_lake_review_packet_validates_for_review_only() -> None:
    report = validate_intake_lake_admission_review_packet(
        _packet(),
        registry_path=REGISTRY,
    )

    assert report["status"] == "passed_candidate_packet_validation"
    assert report["admission_allowed_now"] is False
    assert report["lake_write_authority_now"] is False
    assert report["sqlite_write_authorized_now"] is False
    assert report["raw_payload_storage_allowed"] is False
    assert report["canonical_route_id_assignment"] == "none"
    assert "carrier_rejection_notice" in report["candidate_record_families"]
    assert report["validation_report_hash"] == content_hash(
        {key: value for key, value in report.items() if key != "validation_report_hash"}
    )


def test_packet_validation_rejects_hash_tampering() -> None:
    packet = _packet()
    packet["candidate_record_count"] += 1

    with pytest.raises(IntakeLakeAdmissionReviewPacketError, match="packet_hash"):
        validate_intake_lake_admission_review_packet(packet, registry_path=REGISTRY)


def test_packet_validation_rejects_lake_or_sqlite_authority_claim() -> None:
    packet = _packet()
    packet["admission_controls"]["lake_write_authority_now"] = True
    _rehash_packet(packet)

    with pytest.raises(
        IntakeLakeAdmissionReviewPacketError, match="lake_write_authority_now"
    ):
        validate_intake_lake_admission_review_packet(packet, registry_path=REGISTRY)

    packet = _packet()
    packet["admission_controls"]["sqlite_write_authorized_now"] = True
    _rehash_packet(packet)
    with pytest.raises(
        IntakeLakeAdmissionReviewPacketError, match="sqlite_write_authorized_now"
    ):
        validate_intake_lake_admission_review_packet(packet, registry_path=REGISTRY)


def test_packet_validation_rejects_raw_payload_or_admitted_record() -> None:
    packet = _packet()
    packet["raw_legal_payload"] = {"text": "forbidden"}
    _rehash_packet(packet)

    with pytest.raises(IntakeLakeAdmissionReviewPacketError, match="raw_legal_payload"):
        validate_intake_lake_admission_review_packet(packet, registry_path=REGISTRY)

    packet = _packet()
    packet["candidate_record_summaries"][0]["admission_status"] = "admitted"
    _rehash_record(packet["candidate_record_summaries"][0])
    _rehash_packet(packet)
    with pytest.raises(IntakeLakeAdmissionReviewPacketError, match="not_admitted"):
        validate_intake_lake_admission_review_packet(packet, registry_path=REGISTRY)


def test_packet_validator_cli_writes_local_report(tmp_path: Path) -> None:
    packet_path = tmp_path / "packet.json"
    report_path = tmp_path / "report.json"
    packet_path.write_text(json.dumps(_packet()), encoding="utf-8")

    completed = subprocess.run(
        [
            sys.executable,
            str(VALIDATOR),
            "--packet",
            str(packet_path),
            "--report-out",
            str(report_path),
            "--stdout",
            "json",
        ],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )

    assert completed.returncode == 0, completed.stderr
    stdout_report = json.loads(completed.stdout)
    file_report = json.loads(report_path.read_text(encoding="utf-8"))
    assert stdout_report == file_report
    assert file_report["admission_allowed_now"] is False
    assert file_report["sqlite_write_authorized_now"] is False
