"""PR-06 central Exception Lake admission tests."""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC = REPO_ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from exceptions_lake_runtime.generators.eval_candidate_generator import (  # noqa: E402
    generate_eval_candidate_from_defect,
)
from exceptions_lake_runtime.substrate import reason_codes as rc  # noqa: E402
from exceptions_lake_runtime.validators.admission_validator import (  # noqa: E402
    CentralAdmissionConfig,
    admit_packet,
)
from exceptions_lake_runtime.validators.defect_generator import build_defect_record  # noqa: E402


FIXED_AT = "2026-05-18T00:00:00Z"
SURFACE = json.loads((REPO_ROOT / "contracts.lock.json").read_text(encoding="utf-8"))[
    "contract_surface_lock"
]["surface_sha256"]
WRONG_SURFACE = "0" * 64


def _canonical(payload):
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _rehash(packet: dict) -> dict:
    clean = {k: v for k, v in packet.items() if k != "evidence_packet_hash"}
    packet["evidence_packet_hash"] = hashlib.sha256(_canonical(clean)).hexdigest()
    return packet


def _packet(*, records: list[dict] | None = None) -> dict:
    packet = {
        "schema_version": "evidence_packet.v2",
        "evidence_packet_id": "pkt-pr06",
        "contract_surface_sha256": SURFACE,
        "context_bundle_ref": {"context_bundle_id": "ctx-1", "context_bundle_hash": "a" * 64},
        "execution_authority_records": records
        if records is not None
        else [
            {
                "execution_request_hash": "b" * 64,
                "execution_decision_hash": "c" * 64,
                "execution_passport_hash": "d" * 64,
                "execution_result_hash": "e" * 64,
                "status": "succeeded",
            }
        ],
        "source_refs": [],
        "claim_refs": [],
        "coverage_records": [],
        "verification_records": [],
        "approval_records": [],
        "defect_records": [],
        "manifest_hash": "f" * 64,
        "generated_at": FIXED_AT,
        "run_id": "run-pr06",
        "source_repo": "LawFirm-os-orchestrator",
    }
    return _rehash(packet)


def _config(tmp_path: Path) -> CentralAdmissionConfig:
    return CentralAdmissionConfig(expected_contract_surface_sha256=SURFACE, storage_root=tmp_path)


def test_contract_surface_mismatch_quarantines_packet(tmp_path: Path) -> None:
    packet = _packet()
    packet["contract_surface_sha256"] = WRONG_SURFACE
    _rehash(packet)

    outcome = admit_packet(packet, config=_config(tmp_path), admitted_at=FIXED_AT)

    assert outcome.admission_record["admission_status"] == "quarantined"
    assert outcome.admission_record["admission_reason_code"] == rc.CONTRACT_SURFACE_MISMATCH
    assert outcome.quarantine_record is not None
    assert outcome.execution_record is None


def test_packet_hash_mismatch_quarantines_packet(tmp_path: Path) -> None:
    packet = _packet()
    packet["evidence_packet_hash"] = WRONG_SURFACE

    outcome = admit_packet(packet, config=_config(tmp_path), admitted_at=FIXED_AT)

    assert outcome.admission_record["admission_status"] == "quarantined"
    assert outcome.admission_record["admission_reason_code"] == rc.PACKET_HASH_MISMATCH
    assert outcome.quarantine_record is not None
    assert outcome.execution_record is None


def test_missing_context_bundle_ref_creates_admission_defect(tmp_path: Path) -> None:
    packet = _packet()
    packet.pop("context_bundle_ref")
    _rehash(packet)

    outcome = admit_packet(packet, config=_config(tmp_path), admitted_at=FIXED_AT)

    assert outcome.admission_record["admission_status"] == "rejected"
    assert outcome.admission_record["admission_reason_code"] == rc.MISSING_CONTEXT_BUNDLE_REF
    assert [defect["defect_class"] for defect in outcome.defects] == [rc.EVIDENCE_GAP]
    assert outcome.quarantine_record is None


def test_missing_execution_authority_creates_defect(tmp_path: Path) -> None:
    packet = _packet(records=[])

    outcome = admit_packet(packet, config=_config(tmp_path), admitted_at=FIXED_AT)

    assert outcome.admission_record["admission_status"] == "rejected"
    assert outcome.admission_record["admission_reason_code"] == rc.MISSING_EXECUTION_AUTHORITY
    assert [defect["defect_class"] for defect in outcome.defects] == [rc.EVIDENCE_GAP]


def test_executed_action_without_passport_creates_defect(tmp_path: Path) -> None:
    packet = _packet(
        records=[
            {
                "execution_request_hash": "b" * 64,
                "execution_decision_hash": "c" * 64,
                "execution_result_hash": "e" * 64,
                "status": "succeeded",
            }
        ]
    )

    outcome = admit_packet(packet, config=_config(tmp_path), admitted_at=FIXED_AT)

    assert outcome.admission_record["admission_status"] == "admitted"
    assert [defect["defect_class"] for defect in outcome.defects] == [rc.MISSING_PASSPORT]
    assert outcome.eval_candidates


def test_denied_action_is_stored_as_execution_evidence(tmp_path: Path) -> None:
    denied_record = {
        "execution_request_hash": "b" * 64,
        "execution_decision_hash": "c" * 64,
        "decision": "denied",
        "denial_explanation_hash": "d" * 64,
    }
    packet = _packet(records=[denied_record])

    outcome = admit_packet(packet, config=_config(tmp_path), admitted_at=FIXED_AT)

    assert outcome.admission_record["admission_status"] == "admitted"
    assert outcome.defects == []
    assert outcome.execution_record is not None
    assert outcome.execution_record["denied_action_evidence"] == [denied_record]


def test_allowed_packet_produces_admitted_execution_record(tmp_path: Path) -> None:
    outcome = admit_packet(_packet(), config=_config(tmp_path), admitted_at=FIXED_AT)

    assert outcome.admission_record["admission_status"] == "admitted"
    assert outcome.admission_record["admission_reason_code"] == rc.PASSED_DRY_RUN_ADMISSION
    assert outcome.defects == []
    assert outcome.execution_record is not None
    assert outcome.execution_record["evidence_packet_hash"] == outcome.admission_record["evidence_packet_hash"]
    assert list((tmp_path / "admission_records").glob("*.json"))
    assert list((tmp_path / "execution_records").glob("*.json"))


def test_generated_defects_use_only_registry_defined_classes(tmp_path: Path) -> None:
    cases = []
    mismatch = _packet()
    mismatch["evidence_packet_hash"] = WRONG_SURFACE
    cases.append(mismatch)
    missing_passport = _packet(
        records=[
            {
                "execution_request_hash": "b" * 64,
                "execution_decision_hash": "c" * 64,
                "execution_result_hash": "e" * 64,
                "status": "succeeded",
            }
        ]
    )
    cases.append(missing_passport)

    defects = [
        defect
        for packet in cases
        for defect in admit_packet(packet, config=_config(tmp_path), admitted_at=FIXED_AT).defects
    ]

    assert defects
    assert all(rc.is_registered_defect_class(defect["defect_class"]) for defect in defects)


def test_generated_admission_reasons_use_only_registry_defined_codes(tmp_path: Path) -> None:
    packets = [_packet(), _packet(records=[])]
    packets[1]["execution_authority_records"] = []
    _rehash(packets[1])

    reasons = [
        admit_packet(packet, config=_config(tmp_path), admitted_at=FIXED_AT).admission_record[
            "admission_reason_code"
        ]
        for packet in packets
    ]

    assert all(rc.is_registered_admission_reason_code(reason) for reason in reasons)


def test_eval_candidate_from_high_severity_defect_does_not_mutate_canon() -> None:
    registry_path = (
        REPO_ROOT.parent
        / "LawFirm-os-semantic-substrate"
        / "registry"
        / "runtime-reason-codes-registry.json"
    )
    before = registry_path.read_bytes()
    defect = build_defect_record(
        packet=_packet(),
        defect_class=rc.ROUTE_MISMATCH,
        severity="high",
        description="Route decision diverged from the governed route map.",
        detected_at=FIXED_AT,
    )

    candidate = generate_eval_candidate_from_defect(defect, generated_at=FIXED_AT)

    assert candidate is not None
    assert candidate["promotion_status"] == "candidate"
    assert candidate["source_defect_record_hash"] == defect["defect_record_hash"]
    assert registry_path.read_bytes() == before

