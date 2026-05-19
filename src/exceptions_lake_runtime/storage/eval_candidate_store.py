"""Durable EvalCandidate store (PR-11 proposal-only records)."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from exceptions_lake_runtime.storage._json_store import JsonRecordStore


class EvalCandidateStore:
    def __init__(self, root: str | Path) -> None:
        self._records = JsonRecordStore(root, "eval_candidates")

    def put(self, record: dict[str, Any]) -> Path:
        return self._records.put(record["eval_candidate_hash"], record)

    def get(self, eval_candidate_hash: str) -> dict[str, Any] | None:
        return self._records.get(eval_candidate_hash)

    def list_records(self) -> list[dict[str, Any]]:
        return self._records.list_records()
