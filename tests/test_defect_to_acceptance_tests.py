"""PR-11 defect-to-acceptance-test and synthetic replay tests."""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC = REPO_ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from exceptions_lake_runtime.generators.acceptance_test_generator import (  # noqa: E402
    generate_acceptance_test_steps,
)
from exceptions_lake_runtime.generators.eval_replay import build_synthetic_replay_plan  # noqa: E402
from exceptions_lake_runtime.substrate import reason_codes as rc  # noqa: E402
from exceptions_lake_runtime.validators.admission_validator import (  # noqa: E402
    CentralAdmissionConfig,
    admit_packet,
)
from exceptions_lake_runtime.validators.defect_generator import (  # noqa: E402
    build_defect_record,
    denied_action_recorded_defect,
    missing_passport_defect,
)

FIXED_AT = "2026-05-18T18:00:00Z"
SURFACE = json.loads((REPO_ROOT / "contracts.lock.json").read_text(encoding="utf-8"))[
    "contract_surface_lock"
]["surface_sha256"]


def _canonical(payload: dict) -> bytes:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _rehash(packet: dict) -> dict:
    clean = {k: v for k, v in packet.items() if k != "evidence_packet_hash"}
    packet["evidence_packet_hash"] = hashlib.sha256(_canonical(clean)).hexdigest()
    return packet


def _packet(*, records: list[dict] | None = None) -> dict:
    packet = {
        "schema_version": "evidence_packet.v2",
        "evidence_packet_id": "pkt-pr11-acc",
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
        "source_refs": [{"source_ref_id": "sr-acc"}],
        "claim_refs": [{"claim_ref_id": "cl-acc"}],
        "coverage_records": [],
        "verification_records": [],
        "approval_records": [],
        "defect_records": [],
        "manifest_hash": "f" * 64,
        "generated_at": FIXED_AT,
        "run_id": "run-pr11-acc",
        "source_repo": "LawFirm-os-orchestrator",
    }
    return _rehash(packet)


def _config(tmp_path: Path) -> CentralAdmissionConfig:
    return CentralAdmissionConfig(expected_contract_surface_sha256=SURFACE, storage_root=tmp_path)


def test_missing_passport_generates_acceptance_steps(tmp_path: Path) -> None:
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
    assert any(d["defect_class"] == rc.MISSING_PASSPORT for d in outcome.defects)
    defect = next(d for d in outcome.defects if d["defect_class"] == rc.MISSING_PASSPORT)
    steps = generate_acceptance_test_steps(defect, packet=packet)
    assert any(s["step_id"] == "replay-passport-gate" for s in steps)
    assert outcome.eval_candidates


def test_denied_action_generates_acceptance_test(tmp_path: Path) -> None:
    denied_record = {
        "execution_request_hash": "b" * 64,
        "execution_decision_hash": "c" * 64,
        "decision": "denied",
        "denial_explanation_hash": "d" * 64,
    }
    packet = _packet(records=[denied_record])
    outcome = admit_packet(packet, config=_config(tmp_path), admitted_at=FIXED_AT)
    assert outcome.execution_record is not None
    assert any(d["defect_class"] == rc.DENIED_ACTION_RECORDED for d in outcome.defects)
    defect = next(d for d in outcome.defects if d["defect_class"] == rc.DENIED_ACTION_RECORDED)
    steps = generate_acceptance_test_steps(defect, packet=packet)
    assert any(s["step_id"] == "replay-denied-action-evidence" for s in steps)
    assert outcome.eval_candidates


def test_hash_mismatch_quarantine_mints_eval_candidate(tmp_path: Path) -> None:
    packet = _packet()
    packet["evidence_packet_hash"] = "0" * 64
    outcome = admit_packet(packet, config=_config(tmp_path), admitted_at=FIXED_AT)
    assert outcome.admission_record["admission_status"] == "quarantined"
    assert outcome.defects
    assert any(d["defect_class"] == rc.HASH_MISMATCH for d in outcome.defects)
    assert outcome.eval_candidates


def test_contract_surface_mismatch_generates_acceptance_steps(tmp_path: Path) -> None:
    packet = _packet()
    packet["contract_surface_sha256"] = "0" * 64
    _rehash(packet)
    defect = build_defect_record(
        packet=packet,
        defect_class=rc.HASH_MISMATCH,
        severity="high",
        description="contract surface mismatch synthetic",
        detected_at=FIXED_AT,
    )
    steps = generate_acceptance_test_steps(defect, packet=packet)
    assert any(s["step_id"] == "replay-packet-integrity" for s in steps)


def test_synthetic_replay_plan_is_fixture_only() -> None:
    packet = _packet()
    defect = missing_passport_defect(
        packet=packet,
        authority_record=packet["execution_authority_records"][0],
        detected_at=FIXED_AT,
    )
    plan = build_synthetic_replay_plan(defect, packet=packet)
    assert plan["replay_mode"] == "synthetic_fixture"
    assert plan["contains_production_data"] is False
    assert plan["eval_suite"] == rc.PASSPORT_DENIAL


def test_denied_action_defect_helper_uses_registry_class() -> None:
    packet = _packet(
        records=[
            {
                "execution_request_hash": "b" * 64,
                "execution_decision_hash": "c" * 64,
                "decision": "denied",
                "denial_explanation_hash": "d" * 64,
            }
        ]
    )
    defect = denied_action_recorded_defect(
        packet=packet,
        authority_record=packet["execution_authority_records"][0],
        detected_at=FIXED_AT,
    )
    assert defect["defect_class"] == rc.DENIED_ACTION_RECORDED
