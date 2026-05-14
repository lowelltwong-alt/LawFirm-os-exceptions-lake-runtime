from __future__ import annotations

import json
import os
import shutil
import subprocess
from contextlib import contextmanager
from pathlib import Path

import pytest

from exceptions_lake_runtime.config import CONTRACT_REPO_ENV_VAR, RuntimeConfig
from exceptions_lake_runtime.contract_loader import CONTRACT_LOCK_RELATIVE_PATH

_PYTEST_DEBUG_TEMPROOT = (Path(__file__).resolve().parents[1] / ".pytest-tmp-root").resolve()
_PYTEST_DEBUG_TEMPROOT.mkdir(parents=True, exist_ok=True)
os.environ.setdefault("PYTEST_DEBUG_TEMPROOT", str(_PYTEST_DEBUG_TEMPROOT))


def _source_contract_repo_path() -> Path:
    contract_path = os.getenv(CONTRACT_REPO_ENV_VAR)
    if not contract_path:
        raise RuntimeError(
            f"{CONTRACT_REPO_ENV_VAR} must be set before running tests."
        )
    resolved = Path(contract_path).expanduser().resolve()
    if not resolved.exists():
        raise RuntimeError(f"Contract repo path does not exist: {resolved}")
    return resolved


def _init_git_repo(path: Path) -> None:
    subprocess.run(["git", "init"], cwd=path, check=True, capture_output=True, text=True)
    subprocess.run(
        ["git", "config", "user.name", "Synthetic Test"],
        cwd=path,
        check=True,
        capture_output=True,
        text=True,
    )
    subprocess.run(
        ["git", "config", "user.email", "synthetic-test@example.invalid"],
        cwd=path,
        check=True,
        capture_output=True,
        text=True,
    )
    # Substrate contract fixtures include deep docs paths; Windows MAX_PATH otherwise breaks `git add`.
    subprocess.run(
        ["git", "config", "core.longpaths", "true"],
        cwd=path,
        check=True,
        capture_output=True,
        text=True,
    )
    subprocess.run(["git", "add", "."], cwd=path, check=True, capture_output=True, text=True)
    subprocess.run(
        ["git", "commit", "-m", "contract fixture"],
        cwd=path,
        check=True,
        capture_output=True,
        text=True,
    )


def _git_sha(path: Path) -> str:
    return subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=path,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


@contextmanager
def _pinned_contract_lock(lock_path: Path, contract_sha: str):
    original_lock = json.loads(lock_path.read_text(encoding="utf-8"))
    updated_lock = {**original_lock, "contract_sha": contract_sha}
    lock_path.write_text(json.dumps(updated_lock, indent=2) + "\n", encoding="utf-8")
    try:
        yield
    finally:
        lock_path.write_text(json.dumps(original_lock, indent=2) + "\n", encoding="utf-8")


@pytest.fixture
def contract_repo_copy(tmp_path: Path) -> Path:
    source_root = _source_contract_repo_path()
    target_root = tmp_path / "contract-repo"
    target_root.mkdir(parents=True, exist_ok=True)

    for relative_dir in ("registry", "schemas", "governance", "docs"):
        shutil.copytree(
            source_root / relative_dir,
            target_root / relative_dir,
        )

    _init_git_repo(target_root)
    return target_root


@pytest.fixture
def runtime_repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


@pytest.fixture
def contract_lock_path(runtime_repo_root: Path) -> Path:
    return runtime_repo_root / CONTRACT_LOCK_RELATIVE_PATH


@pytest.fixture
def runtime_config(
    contract_repo_copy: Path,
    contract_lock_path: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> RuntimeConfig:
    monkeypatch.setenv(CONTRACT_REPO_ENV_VAR, str(contract_repo_copy))
    contract_sha = _git_sha(contract_repo_copy)
    with _pinned_contract_lock(contract_lock_path, contract_sha):
        yield RuntimeConfig.from_env(runtime_data_dir=tmp_path / "runtime_data")


@pytest.fixture
def synthetic_event() -> dict:
    example_path = Path(__file__).resolve().parents[1] / "examples" / "synthetic_exception_event.json"
    return json.loads(example_path.read_text(encoding="utf-8"))


@pytest.fixture
def synthetic_envelope(synthetic_event: dict) -> dict:
    return {
        "ingestion_mode": "synthetic_test_only",
        "actor": "synthetic-test-runner",
        "data_flags": {
            "production": False,
            "real_client_data": False,
            "real_matter_data": False,
            "live_connector": False,
        },
        "payload": synthetic_event,
    }


@pytest.fixture
def non_synthetic_readiness_request(runtime_config: RuntimeConfig) -> dict:
    return {
        "source_name": "synthetic-km-slice",
        "source_system_type": "document_repository_export",
        "source_ingestion_manifest_id": "SIM-900001",
        "source_ingestion_manifest_ref": "sim.synthetic.900001",
        "data_classification": "internal_restricted",
        "sensitivity_level": "high",
        "allowed_use_basis": "metadata_only_governed_dry_run",
        "retention_rule": "short_lived_sandbox",
        "access_owner": "synthetic-access-owner",
        "business_owner": "synthetic-business-owner",
        "validation_owner": "synthetic-validation-owner",
        "approval_status": "approved_for_dry_run",
        "rollback_or_quarantine_plan": "quarantine_and_delete_local_runtime_data",
        "evidence_provenance_available": True,
        "contract_sha": _git_sha(runtime_config.contract_repo_root),
        "dry_run_only": True,
    }
