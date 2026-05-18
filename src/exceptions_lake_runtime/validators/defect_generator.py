from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from exceptions_lake_runtime.storage._json_store import content_hash
from exceptions_lake_runtime.substrate.reason_codes import (
    CONTRACT_SURFACE_MISMATCH,
    EVIDENCE_GAP,
    HASH_MISMATCH,
    MISSING_CONTEXT_BUNDLE_REF,
    MISSING_EXECUTION_AUTHORITY,
    MISSING_PASSPORT,
    PACKET_HASH_MISMATCH,
    is_registered_defect_class,
)


SCHEMA_VERSION = "defect_record.v1"


def _iso_utc_now() -> str:
    return datetime.now(tz=UTC).isoformat().replace("+00:00", "Z")


def build_defect_record(
    *,
    packet: dict[str, Any],
    defect_class: str,
    severity: str,
    description: str,
    detected_at: str | None = None,
    execution_request_hash: str | None = None,
) -> dict[str, Any]:
    if not is_registered_defect_class(defect_class):
        raise ValueError(f"unregistered defect class: {defect_class}")
    record: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "defect_record_id": f"def-{content_hash({'packet': packet.get('evidence_packet_hash', ''), 'description': description})[:16]}",
        "contract_surface_sha256": _surface_for_defect(packet),
        "severity": severity,
        "defect_class": defect_class,
        "source_repo": "LawFirm-os-exceptions-lake-runtime-main",
        "evidence_packet_hash": packet.get("evidence_packet_hash", "0" * 64),
        "detected_at": detected_at or _iso_utc_now(),
        "description_hash": content_hash({"description": description}),
        "run_id": packet.get("run_id", ""),
    }
    if execution_request_hash:
        record["execution_request_hash"] = execution_request_hash
    record["defect_record_hash"] = content_hash(record)
    return record


def defects_for_admission_record(
    *,
    packet: dict[str, Any],
    admission_record: dict[str, Any],
    detected_at: str | None = None,
) -> list[dict[str, Any]]:
    reason = admission_record["admission_reason_code"]
    if reason == CONTRACT_SURFACE_MISMATCH:
        return [
            build_defect_record(
                packet=packet,
                defect_class=HASH_MISMATCH,
                severity="high",
                description="EvidencePacket contract surface did not match the lake contract lock.",
                detected_at=detected_at,
            )
        ]
    if reason == PACKET_HASH_MISMATCH:
        return [
            build_defect_record(
                packet=packet,
                defect_class=HASH_MISMATCH,
                severity="high",
                description="EvidencePacket declared hash did not match the recomputed canonical hash.",
                detected_at=detected_at,
            )
        ]
    if reason == MISSING_CONTEXT_BUNDLE_REF:
        return [
            build_defect_record(
                packet=packet,
                defect_class=EVIDENCE_GAP,
                severity="medium",
                description="EvidencePacket was missing the required ContextBundle reference.",
                detected_at=detected_at,
            )
        ]
    if reason == MISSING_EXECUTION_AUTHORITY:
        return [
            build_defect_record(
                packet=packet,
                defect_class=EVIDENCE_GAP,
                severity="high",
                description="EvidencePacket was missing required execution authority records.",
                detected_at=detected_at,
            )
        ]
    return []


def missing_authority_record_defect(
    *,
    packet: dict[str, Any],
    authority_record: dict[str, Any],
    detected_at: str | None = None,
) -> dict[str, Any]:
    return build_defect_record(
        packet=packet,
        defect_class=EVIDENCE_GAP,
        severity="high",
        description="Execution authority record did not include both request and decision hashes.",
        detected_at=detected_at,
        execution_request_hash=authority_record.get("execution_request_hash"),
    )


def missing_passport_defect(
    *,
    packet: dict[str, Any],
    authority_record: dict[str, Any],
    detected_at: str | None = None,
) -> dict[str, Any]:
    return build_defect_record(
        packet=packet,
        defect_class=MISSING_PASSPORT,
        severity="high",
        description="Executed action did not include an execution passport hash.",
        detected_at=detected_at,
        execution_request_hash=authority_record.get("execution_request_hash"),
    )


def _surface_for_defect(packet: dict[str, Any]) -> str:
    surface = packet.get("contract_surface_sha256")
    return surface if isinstance(surface, str) and len(surface) == 64 else "0" * 64

