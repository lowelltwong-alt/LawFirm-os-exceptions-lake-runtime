"""Guard that runtime eval minting does not mutate Semantic Substrate.

This is a Python-level runtime tripwire over the Substrate contract surface. It is
not a substitute for process, filesystem, or OS-level isolation.
"""
from __future__ import annotations

import fnmatch
import hashlib
import json
from pathlib import Path
from typing import Any


def _read_contract_surface_registry(substrate_root: Path) -> dict[str, Any]:
    registry_path = substrate_root / "registry" / "contract-surface-registry.json"
    return json.loads(registry_path.read_text(encoding="utf-8"))


def _selected_surface(registry: dict[str, Any]) -> dict[str, Any]:
    default_surface_id = registry.get("default_surface_id")
    surfaces = registry.get("surfaces") or []
    for surface in surfaces:
        if surface.get("surface_id") == default_surface_id:
            return surface
    if surfaces:
        return surfaces[0]
    raise RuntimeError("contract-surface-registry.json does not define any surfaces")


def _is_excluded(rel: str, exclude_patterns: list[str]) -> bool:
    return any(fnmatch.fnmatch(rel, pattern) for pattern in exclude_patterns)


def _contract_surface_files(substrate_root: Path) -> list[Path]:
    registry = _read_contract_surface_registry(substrate_root)
    surface = _selected_surface(registry)
    include_patterns = [str(p) for p in surface.get("include_patterns") or []]
    exclude_patterns = [str(p) for p in surface.get("exclude_patterns") or []]
    files: dict[str, Path] = {}
    for pattern in include_patterns:
        for path in substrate_root.glob(pattern):
            if not path.is_file():
                continue
            rel = path.relative_to(substrate_root).as_posix()
            if not _is_excluded(rel, exclude_patterns):
                files[rel] = path
    return [files[key] for key in sorted(files)]


def snapshot_substrate_governance_files(substrate_root: Path) -> dict[str, str]:
    """Snapshot hashes of all files included in the active Substrate contract surface."""
    out: dict[str, str] = {}
    for path in _contract_surface_files(substrate_root):
        rel = path.relative_to(substrate_root).as_posix()
        out[rel] = hashlib.sha256(path.read_bytes()).hexdigest()
    return out


def assert_substrate_unchanged(before: dict[str, str], substrate_root: Path) -> None:
    after = snapshot_substrate_governance_files(substrate_root)
    if before != after:
        changed = [k for k in set(before) | set(after) if before.get(k) != after.get(k)]
        raise RuntimeError(
            f"EvalCandidate minting mutated Semantic Substrate governance files: {changed}"
        )
