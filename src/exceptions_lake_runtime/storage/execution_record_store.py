from __future__ import annotations

from pathlib import Path
from typing import Any

from exceptions_lake_runtime.storage._json_store import JsonRecordStore, content_hash


class ExecutionRecordStore:
    """Durable store for lake admission and execution evidence records."""

    def __init__(self, root: str | Path) -> None:
        self._admissions = JsonRecordStore(root, "admission_records")
        self._executions = JsonRecordStore(root, "execution_records")

    def put_admission_record(self, record: dict[str, Any]) -> Path:
        return self._admissions.put(record["admission_record_hash"], record)

    def get_admission_record(self, admission_record_hash: str) -> dict[str, Any] | None:
        return self._admissions.get(admission_record_hash)

    def put_execution_record(self, packet: dict[str, Any], admission_record: dict[str, Any]) -> dict[str, Any]:
        evidence_packet_hash = packet.get("evidence_packet_hash", "")
        record: dict[str, Any] = {
            "schema_version": "exception_lake_execution_record.v1",
            "evidence_packet_hash": evidence_packet_hash,
            "admission_record_hash": admission_record["admission_record_hash"],
            "contract_surface_sha256": packet.get("contract_surface_sha256", ""),
            "run_id": packet.get("run_id", ""),
            "source_repo": packet.get("source_repo", ""),
            "execution_authority_records": list(packet.get("execution_authority_records") or []),
            "denied_action_evidence": _denied_action_records(packet),
        }
        record["execution_record_hash"] = content_hash(record)
        self._executions.put(record["execution_record_hash"], record)
        return record

    def list_admission_records(self) -> list[dict[str, Any]]:
        return self._admissions.list_records()

    def list_execution_records(self) -> list[dict[str, Any]]:
        return self._executions.list_records()


def _denied_action_records(packet: dict[str, Any]) -> list[dict[str, Any]]:
    records = packet.get("execution_authority_records") or []
    return [dict(record) for record in records if is_denied_action(record)]


def is_denied_action(record: dict[str, Any]) -> bool:
    return (
        record.get("decision") == "denied"
        or record.get("status") == "denied"
        or record.get("execution_status") == "denied"
        or record.get("denied") is True
        or bool(record.get("denial_explanation_hash"))
    )
