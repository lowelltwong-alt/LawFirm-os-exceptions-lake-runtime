from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from exceptions_lake_runtime.config import CONTRACT_REPO_ENV_VAR
from exceptions_lake_runtime.contract_loader import HASH_ALGORITHM, ContractLoadError, ContractLoader

SEMANTIC_SUBSTRATE_SCRIPTS = REPO_ROOT.parent / "LawFirm-os-semantic-substrate" / "scripts"

_SURFACE_ID = "lawfirm_os_semantic_substrate.consumer_contract_surface.v1"
_REGISTRY = "registry/contract-surface-registry.json"


def _git_head(repo: Path) -> str:
    return subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def test_committed_tree_surface_matches_canonical_script(runtime_config) -> None:
    if not SEMANTIC_SUBSTRATE_SCRIPTS.is_dir():
        pytest.skip("Sibling LawFirm-os-semantic-substrate/scripts not found")
    repo = runtime_config.contract_repo_root
    sha = _git_head(repo)
    env = {**os.environ, "PYTHONPATH": str(SEMANTIC_SUBSTRATE_SCRIPTS)}
    proc = subprocess.run(
        [
            sys.executable,
            str(SEMANTIC_SUBSTRATE_SCRIPTS / "compute_contract_surface_hash.py"),
            "--substrate",
            str(repo),
            "--ref",
            sha,
        ],
        check=True,
        capture_output=True,
        text=True,
        env=env,
    )
    canonical = json.loads(proc.stdout)
    observed = ContractLoader._compute_contract_surface_hash(
        repo,
        surface_id=_SURFACE_ID,
        registry_path=_REGISTRY,
        commit_ref=sha,
    )
    assert observed == canonical["surface_sha256"]


def test_working_tree_line_endings_do_not_affect_committed_surface_hash(runtime_config) -> None:
    repo = runtime_config.contract_repo_root
    victim = repo / "schemas" / "exception-event.schema.json"
    assert victim.exists()
    original = victim.read_bytes()
    try:
        text = original.decode("utf-8").replace("\r\n", "\n").replace("\n", "\r\n")
        victim.write_bytes(text.encode("utf-8"))
        ContractLoader().load(runtime_config)
    finally:
        victim.write_bytes(original)


def test_missing_pinned_commit_fails_closed(tmp_path: Path) -> None:
    root = tmp_path / "mini-substrate"
    root.mkdir()
    subprocess.run(["git", "init"], cwd=root, check=True, capture_output=True)
    subprocess.run(
        ["git", "config", "user.email", "t@example.invalid"],
        cwd=root,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "t"],
        cwd=root,
        check=True,
        capture_output=True,
    )
    subprocess.run(["git", "config", "core.longpaths", "true"], cwd=root, check=True, capture_output=True)
    (root / "f.txt").write_text("x", encoding="utf-8")
    subprocess.run(["git", "add", "f.txt"], cwd=root, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", "init"], cwd=root, check=True, capture_output=True)
    fake = "f" * 40
    contract_lock = {"contract_sha": fake, "substrate_repo_commit_sha": fake}
    surface_lock = {
        "surface_id": _SURFACE_ID,
        "surface_sha256": "a" * 64,
        "surface_registry_path": _REGISTRY,
        "hash_algorithm": HASH_ALGORITHM,
        "computed_from_commit": fake,
    }
    with pytest.raises(ContractLoadError, match="not present in the contract repo git object database"):
        ContractLoader._validate_contract_surface_lock(root, surface_lock, contract_lock)


def test_missing_committed_surface_registry_is_governed_error(
    contract_repo_copy: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(CONTRACT_REPO_ENV_VAR, str(contract_repo_copy))
    sha = _git_head(contract_repo_copy)
    contract_lock = {"contract_sha": sha, "substrate_repo_commit_sha": sha}
    digest = ContractLoader._compute_contract_surface_hash(
        contract_repo_copy,
        surface_id=_SURFACE_ID,
        registry_path=_REGISTRY,
        commit_ref=sha,
    )
    surface_lock = {
        "surface_id": _SURFACE_ID,
        "surface_sha256": digest,
        "surface_registry_path": _REGISTRY,
        "hash_algorithm": HASH_ALGORITHM,
        "computed_from_commit": sha,
    }
    surface_lock["surface_registry_path"] = "registry/__missing_contract_surface_registry__.json"
    with pytest.raises(ContractLoadError, match="Governed contract surface registry"):
        ContractLoader._validate_contract_surface_lock(contract_repo_copy, surface_lock, contract_lock)


def test_legacy_surface_lock_without_git_pins_hashes_filesystem(
    contract_repo_copy: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(CONTRACT_REPO_ENV_VAR, str(contract_repo_copy))
    sha = _git_head(contract_repo_copy)
    observed = ContractLoader._compute_contract_surface_hash(
        contract_repo_copy,
        surface_id=_SURFACE_ID,
        registry_path=_REGISTRY,
        commit_ref=None,
    )
    surface_lock = {
        "surface_id": _SURFACE_ID,
        "surface_sha256": observed,
        "surface_registry_path": _REGISTRY,
        "hash_algorithm": HASH_ALGORITHM,
    }
    contract_lock = {"contract_sha": sha}
    ContractLoader._validate_contract_surface_lock(contract_repo_copy, surface_lock, contract_lock)
