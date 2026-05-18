from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


def canonical_json(payload: Any) -> bytes:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def content_hash(payload: Any) -> str:
    return hashlib.sha256(canonical_json(payload)).hexdigest()


class JsonRecordStore:
    """Content-addressed JSON file store rooted under one namespace."""

    def __init__(self, root: str | Path, namespace: str) -> None:
        self.root = Path(root).expanduser().resolve() / namespace

    def path_for(self, key: str) -> Path:
        if not key or any(ch in key for ch in "\\/:*?\"<>|"):
            raise ValueError(f"unsafe record key: {key!r}")
        return self.root / f"{key}.json"

    def put(self, key: str, record: dict[str, Any]) -> Path:
        self.root.mkdir(parents=True, exist_ok=True)
        path = self.path_for(key)
        path.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        return path

    def get(self, key: str) -> dict[str, Any] | None:
        path = self.path_for(key)
        if not path.is_file():
            return None
        return json.loads(path.read_text(encoding="utf-8"))

    def list_records(self) -> list[dict[str, Any]]:
        if not self.root.is_dir():
            return []
        return [
            json.loads(path.read_text(encoding="utf-8"))
            for path in sorted(self.root.glob("*.json"))
        ]

