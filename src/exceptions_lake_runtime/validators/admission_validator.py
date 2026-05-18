from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from exceptions_lake_runtime.evidence_packet_admission import (
    AdmissionConfig,
    admit_dry_run,
)
from exceptions_lake_runtime.generators.eval_candidate_generator import (
    generate_eval_candidate_from_defect,
)
from exceptions_lake_runtime.storage._json_store import content_hash
from exceptions_lake_runtime.storage.defect_store import DefectStore
from exceptions_lake_runtime.storage.execution_record_store import (
    ExecutionRecordStore,
    is_denied_action,
)
from exceptions_lake_runtime.storage.quarantine_store import QuarantineStore
from exceptions_lake_runtime.validators.defect_generator import (
    defects_for_admission_record,
    missing_authority_record_defect,
    missing_passport_defect,
)


@dataclass(frozen=True)
class CentralAdmissionConfig:
    expected_contract_surface_sha256: str
    storage_root: str | Path
    source_repo: str = "LawFirm-os-exceptions-lake-runtime-main"

    @classmethod
    def from_contract_lock(cls, *, contract_lock_path: str | Path, storage_root: str | Path) -> "CentralAdmissionConfig":
        lock = json.loads(Path(contract_lock_path).read_text(encoding="utf-8"))
        surface = lock["contract_surface_lock"]["surface_sha256"]
        return cls(expected_contract_surface_sha256=surface, storage_root=storage_root)

    def dry_run_config(self) -> AdmissionConfig:
        return AdmissionConfig(
            expected_contract_surface_sha256=self.expected_contract_surface_sha256,
            source_repo=self.source_repo,
        )


@dataclass(frozen=True)
class AdmissionOutcome:
    admission_record: dict[str, Any]
    execution_record: dict[str, Any] | None
    defects: list[dict[str, Any]]
    eval_candidates: list[dict[str, Any]]
    quarantine_record: dict[str, Any] | None


def admit_packet(
    packet: dict[str, Any],
    *,
    config: CentralAdmissionConfig,
    admitted_at: str | None = None,
) -> AdmissionOutcome:
    """Validate and durably record a PR-06 central admission decision."""

    base_record = admit_dry_run(packet, config=config.dry_run_config(), admitted_at=admitted_at)
    defects = defects_for_admission_record(
        packet=packet,
        admission_record=base_record,
        detected_at=admitted_at,
    )

    if base_record["admission_status"] == "admitted":
        defects.extend(_execution_authority_defects(packet, detected_at=admitted_at))

    defect_store = DefectStore(config.storage_root)
    for defect in defects:
        defect_store.put(defect)

    eval_candidates = [
        candidate
        for defect in defects
        if (candidate := generate_eval_candidate_from_defect(defect, generated_at=admitted_at)) is not None
    ]

    admission_record = _with_defect_refs(
        base_record,
        [defect["defect_record_hash"] for defect in defects],
    )

    execution_store = ExecutionRecordStore(config.storage_root)
    execution_store.put_admission_record(admission_record)

    quarantine_record = None
    if admission_record["admission_status"] == "quarantined":
        quarantine_record = QuarantineStore(config.storage_root).put(packet, admission_record)

    execution_record = None
    if admission_record["admission_status"] == "admitted":
        execution_record = execution_store.put_execution_record(packet, admission_record)

    return AdmissionOutcome(
        admission_record=admission_record,
        execution_record=execution_record,
        defects=defects,
        eval_candidates=eval_candidates,
        quarantine_record=quarantine_record,
    )


def _with_defect_refs(record: dict[str, Any], defect_hashes: list[str]) -> dict[str, Any]:
    updated = dict(record)
    updated["defect_records_minted"] = list(defect_hashes)
    updated.pop("admission_record_hash", None)
    updated["admission_record_hash"] = content_hash(updated)
    return updated


def _execution_authority_defects(packet: dict[str, Any], *, detected_at: str | None) -> list[dict[str, Any]]:
    defects: list[dict[str, Any]] = []
    for record in packet.get("execution_authority_records") or []:
        if not record.get("execution_request_hash") or not record.get("execution_decision_hash"):
            defects.append(
                missing_authority_record_defect(
                    packet=packet,
                    authority_record=record,
                    detected_at=detected_at,
                )
            )
            continue
        if _is_executed_action(record) and not record.get("execution_passport_hash"):
            defects.append(
                missing_passport_defect(
                    packet=packet,
                    authority_record=record,
                    detected_at=detected_at,
                )
            )
    return defects


def _is_executed_action(record: dict[str, Any]) -> bool:
    if is_denied_action(record):
        return False
    return (
        record.get("executed") is True
        or bool(record.get("execution_result_hash"))
        or record.get("status") in {"succeeded", "failed", "executed"}
        or record.get("execution_status") in {"succeeded", "failed", "executed"}
    )

