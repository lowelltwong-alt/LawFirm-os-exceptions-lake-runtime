from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
import importlib.util

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

# Ensure tests load the local in-repo package, not an older installed checkout.
for module_name in (
    "exceptions_lake_runtime",
    "exceptions_lake_runtime.config",
    "exceptions_lake_runtime.contract_loader",
):
    sys.modules.pop(module_name, None)

from exceptions_lake_runtime.config import RuntimeConfig
from exceptions_lake_runtime.contract_loader import ContractLoadError, ContractLoader


def _load_update_contract_lock_module():
    module_path = REPO_ROOT / "scripts" / "update_contract_lock.py"
    spec = importlib.util.spec_from_file_location("update_contract_lock", module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError("Unable to load scripts/update_contract_lock.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_loads_contracts_from_env_var(runtime_config: RuntimeConfig) -> None:
    bundle = ContractLoader().load(runtime_config)

    assert bundle.contract_repo_root == runtime_config.contract_repo_root
    assert bundle.locked_contract_sha == bundle.contract_version
    assert bundle.schema_paths["exception-event-v1"].name == "exception-event.schema.json"
    assert bundle.schema_paths["pressure-vector-v1"].name == "pressure-vector.schema.json"
    assert "exceptions_lake_boundary" in bundle.boundary_doc_paths
    assert "ai_control_plane_boundary" in bundle.boundary_doc_paths
    assert bundle.export_manifest_present is True
    assert bundle.export_manifest is not None
    assert "evaluation-run-schema-v1" in bundle.schema_paths


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
    assert "exceptions_lake_boundary" in bundle.boundary_doc_paths
    assert "ai_control_plane_boundary" in bundle.boundary_doc_paths


def test_fails_closed_when_export_manifest_is_malformed_json(
    runtime_config: RuntimeConfig,
) -> None:
    export_manifest_path = (
        runtime_config.contract_repo_root
        / "registry"
        / "exceptions-lake-contract-export.json"
    )
    export_manifest_path.write_text("{ malformed", encoding="utf-8")

    with pytest.raises(ContractLoadError, match="Invalid JSON"):
        ContractLoader().load(runtime_config)


def test_fails_closed_when_export_manifest_missing_required_fields(
    runtime_config: RuntimeConfig,
) -> None:
    export_manifest_path = (
        runtime_config.contract_repo_root
        / "registry"
        / "exceptions-lake-contract-export.json"
    )
    manifest = json.loads(export_manifest_path.read_text(encoding="utf-8"))
    manifest.pop("canonical_schema_keys", None)
    export_manifest_path.write_text(
        json.dumps(manifest, indent=2) + "\n",
        encoding="utf-8",
    )

    with pytest.raises(
        ContractLoadError, match="Invalid export manifest field 'canonical_schema_keys'"
    ):
        ContractLoader().load(runtime_config)


def test_fails_closed_when_export_manifest_contains_invalid_required_doc_path(
    runtime_config: RuntimeConfig,
) -> None:
    export_manifest_path = (
        runtime_config.contract_repo_root
        / "registry"
        / "exceptions-lake-contract-export.json"
    )
    manifest = json.loads(export_manifest_path.read_text(encoding="utf-8"))
    manifest["required_docs"] = [
        "governance/EXCEPTIONS_LAKE_BOUNDARY.md",
        "governance/THIS_PATH_DOES_NOT_EXIST.md",
    ]
    export_manifest_path.write_text(
        json.dumps(manifest, indent=2) + "\n",
        encoding="utf-8",
    )

    with pytest.raises(
        ContractLoadError,
        match="Required contract path is missing: governance/THIS_PATH_DOES_NOT_EXIST.md",
    ):
        ContractLoader().load(runtime_config)


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


def test_fails_closed_when_lock_missing_required_field(
    runtime_config: RuntimeConfig, contract_lock_path: Path
) -> None:
    original_lock = json.loads(contract_lock_path.read_text(encoding="utf-8"))
    invalid_lock = dict(original_lock)
    invalid_lock.pop("generated_by", None)
    contract_lock_path.write_text(
        json.dumps(invalid_lock, indent=2) + "\n",
        encoding="utf-8",
    )

    try:
        with pytest.raises(
            ContractLoadError,
            match="contracts.lock.json is missing required field\\(s\\): generated_by",
        ):
            ContractLoader().load(runtime_config)
    finally:
        contract_lock_path.write_text(
            json.dumps(original_lock, indent=2) + "\n",
            encoding="utf-8",
        )


def test_fails_closed_when_lock_shape_is_invalid(
    runtime_config: RuntimeConfig, contract_lock_path: Path
) -> None:
    original_lock = contract_lock_path.read_text(encoding="utf-8")
    contract_lock_path.write_text('["invalid", "shape"]\n', encoding="utf-8")

    try:
        with pytest.raises(
            ContractLoadError,
            match="contracts.lock.json is invalid: expected a JSON object",
        ):
            ContractLoader().load(runtime_config)
    finally:
        contract_lock_path.write_text(original_lock, encoding="utf-8")


def test_update_contract_lock_build_document_is_deterministic() -> None:
    module = _load_update_contract_lock_module()
    fixed_timestamp = "2026-05-04T14:00:00Z"

    lock_a = module.build_lock_document(
        "abc123", generated_at=fixed_timestamp
    )
    lock_b = module.build_lock_document(
        "abc123", generated_at=fixed_timestamp
    )

    assert lock_a == lock_b
    assert list(lock_a.keys())[:5] == [
        "contract_repo",
        "contract_ref_type",
        "contract_sha",
        "generated_at",
        "generated_by",
    ]
