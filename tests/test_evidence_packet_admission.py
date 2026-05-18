"""Tests for the PR-05 dry-run EvidencePacket v2 admission adapter."""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC = REPO_ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from exceptions_lake_runtime.evidence_packet_admission import (
    AdmissionConfig,
    admit_dry_run,
)


SURFACE = "9787216aae3f0ef343009f961addce8cc5fcb6697b9a40243ff0176a3e4d0b34"
WRONG = "0" * 64


def _canonical(d):
    return json.dumps(d, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _good_packet():
    p = {
        "schema_version": "evidence_packet.v2",
        "evidence_packet_id": "pkt-1",
        "contract_surface_sha256": SURFACE,
        "context_bundle_ref": {"context_bundle_id": "ctx-1", "context_bundle_hash": "a" * 64},
        "execution_authority_records": [
            {"execution_request_hash": "b" * 64, "execution_decision_hash": "c" * 64}
        ],
        "source_refs": [],
        "claim_refs": [],
        "coverage_records": [],
        "verification_records": [],
        "approval_records": [],
        "defect_records": [],
        "manifest_hash": "0" * 64,
        "generated_at": "2026-05-18T00:00:00Z",
        "run_id": "run-1",
        "source_repo": "LawFirm-os-orchestrator",
    }
    clean = {k: v for k, v in p.items() if k != "evidence_packet_hash"}
    p["evidence_packet_hash"] = hashlib.sha256(_canonical(clean)).hexdigest()
    return p


CONFIG = AdmissionConfig(expected_contract_surface_sha256=SURFACE)


def test_well_formed_packet_is_admitted():
    rec = admit_dry_run(_good_packet(), config=CONFIG, admitted_at="2026-05-18T00:00:01Z")
    assert rec["admission_status"] == "admitted"
    assert rec["admission_reason_code"] == "passed_dry_run_admission"
    assert len(rec["admission_record_hash"]) == 64
    assert rec["context_bundle_hash"] == "a" * 64


def test_wrong_schema_version_is_rejected():
    p = _good_packet()
    p["schema_version"] = "evidence_packet.v1"
    rec = admit_dry_run(p, config=CONFIG)
    assert rec["admission_status"] == "rejected"
    assert rec["admission_reason_code"] == "wrong_packet_schema"


def test_missing_contract_surface_is_rejected():
    p = _good_packet()
    p["contract_surface_sha256"] = ""
    rec = admit_dry_run(p, config=CONFIG)
    assert rec["admission_status"] == "rejected"
    assert rec["admission_reason_code"] == "missing_contract_surface"


def test_wrong_contract_surface_is_quarantined():
    p = _good_packet()
    p["contract_surface_sha256"] = WRONG
    # Re-hash so packet_hash matches the tampered surface — we want to exercise
    # the contract_surface_mismatch branch, not packet_hash_mismatch.
    clean = {k: v for k, v in p.items() if k != "evidence_packet_hash"}
    p["evidence_packet_hash"] = hashlib.sha256(_canonical(clean)).hexdigest()
    rec = admit_dry_run(p, config=CONFIG)
    assert rec["admission_status"] == "quarantined"
    assert rec["admission_reason_code"] == "contract_surface_mismatch"


def test_missing_context_bundle_ref_is_rejected():
    p = _good_packet()
    del p["context_bundle_ref"]
    clean = {k: v for k, v in p.items() if k != "evidence_packet_hash"}
    p["evidence_packet_hash"] = hashlib.sha256(_canonical(clean)).hexdigest()
    rec = admit_dry_run(p, config=CONFIG)
    assert rec["admission_status"] == "rejected"
    assert rec["admission_reason_code"] == "missing_context_bundle_ref"


def test_missing_execution_authority_is_rejected():
    p = _good_packet()
    p["execution_authority_records"] = []
    clean = {k: v for k, v in p.items() if k != "evidence_packet_hash"}
    p["evidence_packet_hash"] = hashlib.sha256(_canonical(clean)).hexdigest()
    rec = admit_dry_run(p, config=CONFIG)
    assert rec["admission_status"] == "rejected"
    assert rec["admission_reason_code"] == "missing_execution_authority"


def test_tampered_packet_hash_is_quarantined():
    p = _good_packet()
    p["evidence_packet_hash"] = "0" * 64  # tamper without re-hashing
    rec = admit_dry_run(p, config=CONFIG)
    assert rec["admission_status"] == "quarantined"
    assert rec["admission_reason_code"] == "packet_hash_mismatch"


def test_admission_record_hash_is_chainable():
    rec1 = admit_dry_run(_good_packet(), config=CONFIG, admitted_at="2026-05-18T00:00:01Z")
    rec2 = admit_dry_run(_good_packet(), config=CONFIG, admitted_at="2026-05-18T00:00:01Z")
    # Same inputs (including admitted_at) -> same record hash.
    assert rec1["admission_record_hash"] == rec2["admission_record_hash"]
