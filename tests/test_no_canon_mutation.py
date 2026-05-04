from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path

import pytest

from exceptions_lake_runtime.audit_log import AuditLog
from exceptions_lake_runtime.config import RuntimeConfig, RuntimeConfigError
from exceptions_lake_runtime.contract_loader import ContractLoader
from exceptions_lake_runtime.event_ingestion import EventIngestionService
from exceptions_lake_runtime.event_store import EventStore
from exceptions_lake_runtime.non_synthetic_readiness import NonSyntheticReadinessChecker
from exceptions_lake_runtime.policy_gateway import PolicyGateway
from exceptions_lake_runtime.pressure_builder import PressureBuilder
from exceptions_lake_runtime.validation_gateway import ValidationGateway


def _snapshot_repo_contents(root: Path) -> dict[str, str]:
    snapshot: dict[str, str] = {}
    for file_path in sorted(root.rglob("*")):
        if not file_path.is_file():
            continue
        if ".git" in file_path.parts:
            continue
        digest = hashlib.sha256(file_path.read_bytes()).hexdigest()
        snapshot[str(file_path.relative_to(root))] = digest
    return snapshot


def _build_service(runtime_config: RuntimeConfig):
    bundle = ContractLoader().load(runtime_config)
    event_store = EventStore(runtime_config.event_store_path)
    audit_log = AuditLog(runtime_config.audit_log_path)
    service = EventIngestionService(
        contract_bundle=bundle,
        validation_gateway=ValidationGateway(bundle),
        policy_gateway=PolicyGateway(bundle.contract_version),
        event_store=event_store,
        audit_log=audit_log,
        non_synthetic_readiness_checker=NonSyntheticReadinessChecker(
            bundle.locked_contract_sha or bundle.contract_version
        ),
    )
    return bundle, event_store, service


def test_runtime_data_path_nested_inside_contract_repo_is_rejected(
    contract_repo_copy: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("EXCEPTIONS_LAKE_CONTRACT_REPO_PATH", str(contract_repo_copy))

    with pytest.raises(RuntimeConfigError):
        RuntimeConfig.from_env(runtime_data_dir=contract_repo_copy / "runtime_data")


def test_ingestion_does_not_modify_contract_repo_files(
    runtime_config: RuntimeConfig, synthetic_envelope: dict
) -> None:
    before_snapshot = _snapshot_repo_contents(runtime_config.contract_repo_root)
    _, _, service = _build_service(runtime_config)

    result = service.ingest(copy.deepcopy(synthetic_envelope))

    after_snapshot = _snapshot_repo_contents(runtime_config.contract_repo_root)
    assert result["accepted"] is True
    assert before_snapshot == after_snapshot


def test_event_and_audit_writes_stay_under_runtime_data(
    runtime_config: RuntimeConfig, synthetic_envelope: dict
) -> None:
    bundle, event_store, service = _build_service(runtime_config)

    _ = bundle
    service.ingest(copy.deepcopy(synthetic_envelope))

    assert runtime_config.event_store_path.exists()
    assert runtime_config.audit_log_path.exists()
    assert runtime_config.event_store_path.parent == runtime_config.runtime_data_dir
    assert runtime_config.audit_log_path.parent == runtime_config.runtime_data_dir
    assert runtime_config.contract_repo_root not in runtime_config.event_store_path.parents
    assert runtime_config.contract_repo_root not in runtime_config.audit_log_path.parents


def test_contract_loader_reads_but_does_not_write_contract_repo(
    runtime_config: RuntimeConfig,
) -> None:
    before_snapshot = _snapshot_repo_contents(runtime_config.contract_repo_root)

    bundle = ContractLoader().load(runtime_config)

    after_snapshot = _snapshot_repo_contents(runtime_config.contract_repo_root)
    assert bundle.contract_repo_root == runtime_config.contract_repo_root
    assert before_snapshot == after_snapshot


def test_pressure_builder_returns_derived_candidate_only(
    runtime_config: RuntimeConfig, synthetic_envelope: dict
) -> None:
    bundle, event_store, service = _build_service(runtime_config)
    service.ingest(copy.deepcopy(synthetic_envelope))

    builder = PressureBuilder(bundle, event_store=event_store)
    candidate = builder.build_candidate()

    assert candidate["candidate_status"] == "synthetic_candidate_not_canonical"
    assert candidate["contract_version"] == bundle.contract_version
    assert candidate["pressure_vector"]["schema_type"] == "pressure-vector"


def test_pressure_builder_does_not_persist_to_contract_repo(
    runtime_config: RuntimeConfig, synthetic_envelope: dict
) -> None:
    before_snapshot = _snapshot_repo_contents(runtime_config.contract_repo_root)
    bundle, event_store, service = _build_service(runtime_config)
    service.ingest(copy.deepcopy(synthetic_envelope))

    builder = PressureBuilder(bundle, event_store=event_store)
    _ = builder.build_candidate()

    after_snapshot = _snapshot_repo_contents(runtime_config.contract_repo_root)
    assert before_snapshot == after_snapshot
