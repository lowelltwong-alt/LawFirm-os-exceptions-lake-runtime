from __future__ import annotations

from pathlib import Path
from typing import Any

from exceptions_lake_runtime.storage._json_store import JsonRecordStore


class DefectStore:
    """Durable DefectRecord store."""

    def __init__(self, root: str | Path) -> None:
        self._records = JsonRecordStore(root, "defect_records")

    def put(self, record: dict[str, Any]) -> Path:
        return self._records.put(record["defect_record_hash"], record)

    def get(self, defect_record_hash: str) -> dict[str, Any] | None:
        return self._records.get(defect_record_hash)

    def list_records(self) -> list[dict[str, Any]]:
        return self._records.list_records()

