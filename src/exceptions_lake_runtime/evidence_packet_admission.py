"""Dry-run EvidencePacket v2 admission adapter (PR-05).

Lake-side counterpart to the orchestrator's build_evidence_packet_v2.
Validates structure and the inner packet_hash, then returns an
ExceptionLakeAdmissionRecord dict.

This is a dry-run adapter: it does NOT persist. PR-06 will add the
durable storage adapter alongside this. Keeping admission validation
separate from storage lets the orchestrator dry-run packets in CI
without writing to the lake.

Substrate schemas:
  - evidence-packet.v2
  - exception-lake-admission-record.v1
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any


SCHEMA_VERSION = "exception_lake_admission_record.v1"


@dataclass(frozen=True)
class AdmissionConfig:
    expected_contract_surface_sha256: str
    source_repo: str = "LawFirm-os-exceptions-lake-runtime"


def _iso_utc_now() -> str:
    return datetime.now(tz=UTC).isoformat().replace("+00:00", "Z")


def _canonical_json(d: Any) -> bytes:
    return json.dumps(d, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _recompute_packet_hash(payload: dict[str, Any]) -> str:
    clean = {k: v for k, v in payload.items() if k != "evidence_packet_hash"}
    return hashlib.sha256(_canonical_json(clean)).hexdigest()


def _record(
    *,
    admission_status: str,
    admission_reason_code: str,
    evidence_packet_hash: str,
    contract_surface_sha256: str,
    context_bundle_hash: str | None,
    config: AdmissionConfig,
    admitted_at: str | None,
) -> dict[str, Any]:
    rec: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "admission_record_id": f"adm-{admitted_at or _iso_utc_now()}",
        "evidence_packet_hash": evidence_packet_hash,
        "contract_surface_sha256": contract_surface_sha256,
        "admitted_at": admitted_at or _iso_utc_now(),
        "admission_status": admission_status,
        "admission_reason_code": admission_reason_code,
        "source_repo": config.source_repo,
        "defect_records_minted": [],
    }
    if context_bundle_hash:
        rec["context_bundle_hash"] = context_bundle_hash
    # Hash the record itself (excluding admission_record_hash) so the lake can chain it.
    rec_no_hash = {k: v for k, v in rec.items() if k != "admission_record_hash"}
    rec["admission_record_hash"] = hashlib.sha256(_canonical_json(rec_no_hash)).hexdigest()
    return rec


def admit_dry_run(packet: dict[str, Any], *, config: AdmissionConfig, admitted_at: str | None = None) -> dict[str, Any]:
    """Validate the packet structure and return an admission record.

    Status decision (in order):
      - schema_version != evidence_packet.v2          -> rejected (wrong_packet_schema)
      - missing contract_surface_sha256               -> rejected (missing_contract_surface)
      - contract_surface_sha256 mismatch              -> quarantined (contract_surface_mismatch)
      - missing context_bundle_ref                    -> rejected (missing_context_bundle_ref)
      - missing/empty execution_authority_records     -> rejected (missing_execution_authority)
      - recomputed packet hash != declared hash       -> quarantined (packet_hash_mismatch)
      - otherwise                                     -> admitted
    """
    declared_hash = packet.get("evidence_packet_hash", "")
    contract_surface = packet.get("contract_surface_sha256", "")
    context_bundle_ref = packet.get("context_bundle_ref") or {}
    context_bundle_hash = context_bundle_ref.get("context_bundle_hash") if isinstance(context_bundle_ref, dict) else None

    if packet.get("schema_version") != "evidence_packet.v2":
        return _record(
            admission_status="rejected",
            admission_reason_code="wrong_packet_schema",
            evidence_packet_hash=declared_hash,
            contract_surface_sha256=contract_surface or "",
            context_bundle_hash=context_bundle_hash,
            config=config,
            admitted_at=admitted_at,
        )
    if not contract_surface:
        return _record(
            admission_status="rejected",
            admission_reason_code="missing_contract_surface",
            evidence_packet_hash=declared_hash,
            contract_surface_sha256="",
            context_bundle_hash=context_bundle_hash,
            config=config,
            admitted_at=admitted_at,
        )
    if contract_surface != config.expected_contract_surface_sha256:
        return _record(
            admission_status="quarantined",
            admission_reason_code="contract_surface_mismatch",
            evidence_packet_hash=declared_hash,
            contract_surface_sha256=contract_surface,
            context_bundle_hash=context_bundle_hash,
            config=config,
            admitted_at=admitted_at,
        )
    if not isinstance(context_bundle_ref, dict) or not context_bundle_hash:
        return _record(
            admission_status="rejected",
            admission_reason_code="missing_context_bundle_ref",
            evidence_packet_hash=declared_hash,
            contract_surface_sha256=contract_surface,
            context_bundle_hash=context_bundle_hash,
            config=config,
            admitted_at=admitted_at,
        )
    eauth = packet.get("execution_authority_records")
    if not isinstance(eauth, list) or not eauth:
        return _record(
            admission_status="rejected",
            admission_reason_code="missing_execution_authority",
            evidence_packet_hash=declared_hash,
            contract_surface_sha256=contract_surface,
            context_bundle_hash=context_bundle_hash,
            config=config,
            admitted_at=admitted_at,
        )
    observed_hash = _recompute_packet_hash(packet)
    if observed_hash != declared_hash:
        return _record(
            admission_status="quarantined",
            admission_reason_code="packet_hash_mismatch",
            evidence_packet_hash=declared_hash,
            contract_surface_sha256=contract_surface,
            context_bundle_hash=context_bundle_hash,
            config=config,
            admitted_at=admitted_at,
        )
    return _record(
        admission_status="admitted",
        admission_reason_code="passed_dry_run_admission",
        evidence_packet_hash=declared_hash,
        contract_surface_sha256=contract_surface,
        context_bundle_hash=context_bundle_hash,
        config=config,
        admitted_at=admitted_at,
    )
