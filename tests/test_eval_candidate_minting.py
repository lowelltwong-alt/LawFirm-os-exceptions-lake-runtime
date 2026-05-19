"""PR-11 EvalCandidate minting tests."""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC = REPO_ROOT / "src"
SUBSTRATE = REPO_ROOT.parent / "LawFirm-os-semantic-substrate"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from exceptions_lake_runtime.generators.eval_candidate_from_defect import mint_eval_candidate  # noqa: E402
from exceptions_lake_runtime.generators.eval_candidate_generator import (  # noqa: E402
    generate_eval_candidate_from_defect,
)
from exceptions_lake_runtime.storage._json_store import content_hash  # noqa: E402
from exceptions_lake_runtime.substrate import reason_codes as rc  # noqa: E402
from exceptions_lake_runtime.validators.defect_generator import build_defect_record  # noqa: E402

FIXED_AT = "2026-05-18T18:00:00Z"
SURFACE = json.loads((REPO_ROOT / "contracts.lock.json").read_text(encoding="utf-8"))[
    "contract_surface_lock"
]["surface_sha256"]


def _packet(**overrides) -> dict:
    packet = {
        "schema_version": "evidence_packet.v2",
        "evidence_packet_id": "pkt-pr11",
        "contract_surface_sha256": SURFACE,
        "context_bundle_ref": {"context_bundle_id": "ctx-1", "context_bundle_hash": "a" * 64},
        "execution_authority_records": [
            {
                "execution_request_hash": "b" * 64,
                "execution_decision_hash": "c" * 64,
                "execution_passport_hash": "d" * 64,
                "execution_result_hash": "e" * 64,
                "status": "succeeded",
            }
        ],
        "source_refs": [{"source_ref_id": "sr-1"}],
        "claim_refs": [{"claim_ref_id": "cl-1"}],
        "coverage_records": [],
        "verification_records": [],
        "approval_records": [],
        "defect_records": [],
        "manifest_hash": "f" * 64,
        "generated_at": FIXED_AT,
        "run_id": "run-pr11",
        "source_repo": "LawFirm-os-orchestrator",
    }
    packet.update(overrides)
    clean = {k: v for k, v in packet.items() if k != "evidence_packet_hash"}
    packet["evidence_packet_hash"] = hashlib.sha256(
        json.dumps(clean, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    ).hexdigest()
    return packet


def _defect(*, defect_class: str, severity: str) -> dict:
    return build_defect_record(
        packet=_packet(),
        defect_class=defect_class,
        severity=severity,
        description=f"synthetic {defect_class} for PR-11",
        detected_at=FIXED_AT,
    )


def test_high_severity_defect_mints_eval_candidate() -> None:
    defect = _defect(defect_class=rc.MISSING_PASSPORT, severity="high")
    candidate = generate_eval_candidate_from_defect(defect, packet=_packet(), generated_at=FIXED_AT)
    assert candidate is not None
    assert candidate["promotion_status"] == "candidate"
    assert candidate["source_defect_record_hash"] == defect["defect_record_hash"]
    assert candidate["evidence_packet_hash"] == defect["evidence_packet_hash"]
    assert candidate["eval_class"] == rc.PASSPORT_DENIAL


def test_low_severity_defect_does_not_mint() -> None:
    defect = _defect(defect_class=rc.EVIDENCE_GAP, severity="medium")
    assert generate_eval_candidate_from_defect(defect, generated_at=FIXED_AT) is None


def test_eval_candidate_hash_chains_to_defect() -> None:
    defect = _defect(defect_class=rc.HASH_MISMATCH, severity="critical")
    candidate = generate_eval_candidate_from_defect(defect, generated_at=FIXED_AT)
    assert candidate is not None
    assert candidate["eval_candidate_hash"] == content_hash(
        {k: v for k, v in candidate.items() if k != "eval_candidate_hash"}
    )
    assert candidate["source_defect_record_hash"] == defect["defect_record_hash"]


def test_minting_does_not_mutate_substrate() -> None:
    defect = _defect(defect_class=rc.ROUTE_MISMATCH, severity="high")
    candidate = mint_eval_candidate(
        defect,
        packet=_packet(),
        generated_at=FIXED_AT,
        substrate_root=SUBSTRATE,
    )
    assert candidate is not None


def test_generated_candidates_use_registry_defect_classes_only() -> None:
    for defect_class in (rc.MISSING_PASSPORT, rc.HASH_MISMATCH, rc.DENIED_ACTION_RECORDED):
        defect = _defect(defect_class=defect_class, severity="high")
        candidate = generate_eval_candidate_from_defect(defect, generated_at=FIXED_AT)
        assert candidate is not None
        assert rc.is_registered_defect_class(defect_class)
        assert candidate["eval_class"] in rc.DEFECT_CLASSES or candidate["eval_class"] in {
            rc.EVIDENCE_GAP,
            rc.PASSPORT_DENIAL,
        }


def test_unregistered_defect_class_raises() -> None:
    defect = _defect(defect_class=rc.MISSING_PASSPORT, severity="high")
    defect["defect_class"] = "not_a_registered_defect_class"
    with pytest.raises(ValueError, match="unregistered"):
        generate_eval_candidate_from_defect(defect, generated_at=FIXED_AT)
