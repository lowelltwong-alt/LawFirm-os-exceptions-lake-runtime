from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from exceptions_lake_runtime.config import RuntimeConfig
from exceptions_lake_runtime.contract_loader import ContractLoadError, ContractLoader


def test_loads_contracts_from_env_var(runtime_config: RuntimeConfig) -> None:
    bundle = ContractLoader().load(runtime_config)

    assert bundle.contract_repo_root == runtime_config.contract_repo_root
    assert bundle.locked_contract_sha == bundle.contract_version
    assert bundle.schema_paths["exception-event-v1"].name == "exception-event.schema.json"
    assert bundle.schema_paths["pressure-vector-v1"].name == "pressure-vector.schema.json"
    assert "exceptions_lake_boundary" in bundle.boundary_doc_paths
    assert "ai_control_plane_boundary" in bundle.boundary_doc_paths


def test_falls_back_when_export_manifest_absent(runtime_config: RuntimeConfig) -> None:
    export_manifest_path = (
        runtime_config.contract_repo_root
        / "registry"
        / "exceptions-lake-contract-export.json"
    )
    if export_manifest_path.exists():
        export_manifest_path.unlink()

    bundle = ContractLoader().load(runtime_config)

    assert bundle.export_manifest_present is False
    assert bundle.export_manifest is None
    assert "adaptation-proposal-v1" in bundle.schema_paths
    assert "access-decision-schema-v1" in bundle.schema_paths


def test_fails_closed_when_required_schema_path_missing(
    contract_repo_copy: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    missing_path = contract_repo_copy / "schemas" / "pressure-vector.schema.json"
    missing_path.unlink()

    monkeypatch.setenv("EXCEPTIONS_LAKE_CONTRACT_REPO_PATH", str(contract_repo_copy))
    config = RuntimeConfig.from_env(runtime_data_dir=tmp_path / "runtime_data")

    with pytest.raises(ContractLoadError):
        ContractLoader().load(config)


def test_records_contract_git_sha(runtime_config: RuntimeConfig) -> None:
    expected_sha = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=runtime_config.contract_repo_root,
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()

    bundle = ContractLoader().load(runtime_config)

    assert bundle.contract_version == expected_sha


def test_fails_closed_when_live_contract_sha_mismatches_lock(
    runtime_config: RuntimeConfig, contract_lock_path: Path
) -> None:
    original_lock = json.loads(contract_lock_path.read_text(encoding="utf-8"))
    contract_lock_path.write_text(
        json.dumps({**original_lock, "contract_sha": "deadbeef"}, indent=2) + "\n",
        encoding="utf-8",
    )

    try:
        with pytest.raises(ContractLoadError):
            ContractLoader().load(runtime_config)
    finally:
        contract_lock_path.write_text(
            json.dumps(original_lock, indent=2) + "\n",
            encoding="utf-8",
        )
