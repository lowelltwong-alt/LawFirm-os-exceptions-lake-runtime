from __future__ import annotations

from pathlib import Path
from typing import Any

from exceptions_lake_runtime.storage._json_store import JsonRecordStore, content_hash


class QuarantineStore:
    """Durable store for quarantined packets and the admission record explaining why."""

    def __init__(self, root: str | Path) -> None:
        self._records = JsonRecordStore(root, "quarantine_records")

    def put(self, packet: dict[str, Any], admission_record: dict[str, Any]) -> dict[str, Any]:
        record: dict[str, Any] = {
            "schema_version": "exception_lake_quarantine_record.v1",
            "evidence_packet_hash": packet.get("evidence_packet_hash", ""),
            "admission_record_hash": admission_record["admission_record_hash"],
            "admission_reason_code": admission_record["admission_reason_code"],
            "contract_surface_sha256": packet.get("contract_surface_sha256", ""),
            "packet": packet,
        }
        record["quarantine_record_hash"] = content_hash(record)
        self._records.put(record["quarantine_record_hash"], record)
        return record

    def list_records(self) -> list[dict[str, Any]]:
        return self._records.list_records()

