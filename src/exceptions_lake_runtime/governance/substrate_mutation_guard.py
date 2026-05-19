"""Guard that runtime eval minting does not mutate Semantic Substrate (PR-11)."""
from __future__ import annotations

import hashlib
from pathlib import Path


def snapshot_substrate_governance_files(substrate_root: Path) -> dict[str, str]:
    """Snapshot hashes of substrate governance files that must never change at runtime."""
    watch = [
        "registry/runtime-reason-codes-registry.json",
        "registry/schema-registry.json",
        "registry/contract-surface-registry.json",
        "schemas/defect-record.schema.json",
        "schemas/eval-candidate.schema.json",
    ]
    out: dict[str, str] = {}
    for rel in watch:
        path = substrate_root / rel
        if path.is_file():
            out[rel] = hashlib.sha256(path.read_bytes()).hexdigest()
    return out


def assert_substrate_unchanged(before: dict[str, str], substrate_root: Path) -> None:
    after = snapshot_substrate_governance_files(substrate_root)
    if before != after:
        changed = [k for k in set(before) | set(after) if before.get(k) != after.get(k)]
        raise RuntimeError(
            f"EvalCandidate minting mutated Semantic Substrate governance files: {changed}"
        )
