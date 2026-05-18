from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from exceptions_lake_runtime.contract_loader import HASH_ALGORITHM, ContractLoader


def test_update_contract_lock_document_can_include_surface_lock() -> None:
    import importlib.util
    module_path = REPO_ROOT / "scripts" / "update_contract_lock.py"
    spec = importlib.util.spec_from_file_location("update_contract_lock", module_path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    surface = {
        "surface_id": "lawfirm_os_semantic_substrate.consumer_contract_surface.v1",
        "surface_sha256": "a" * 64,
        "surface_registry_path": "registry/contract-surface-registry.json",
        "hash_algorithm": HASH_ALGORITHM,
        "computed_from_repo": "LawFirm-os-semantic-substrate",
        "computed_from_commit": "b" * 40,
    }
    document = module.build_lock_document("b" * 40, generated_at="2026-01-01T00:00:00Z", surface_lock=surface)
    assert document["contract_surface_lock"] == surface
    assert document["substrate_repo_commit_sha"] == "b" * 40
