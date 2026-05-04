from __future__ import annotations

import copy

from exceptions_lake_runtime.audit_log import AuditLog
from exceptions_lake_runtime.contract_loader import ContractLoader
from exceptions_lake_runtime.event_ingestion import EventIngestionService
from exceptions_lake_runtime.event_store import EventStore
from exceptions_lake_runtime.non_synthetic_readiness import NonSyntheticReadinessChecker
from exceptions_lake_runtime.policy_gateway import PolicyGateway
from exceptions_lake_runtime.validation_gateway import ValidationGateway


def _build_service(runtime_config):
    bundle = ContractLoader().load(runtime_config)
    event_store = EventStore(runtime_config.event_store_path)
    audit_log = AuditLog(runtime_config.audit_log_path)
    return EventIngestionService(
        contract_bundle=bundle,
        validation_gateway=ValidationGateway(bundle),
        policy_gateway=PolicyGateway(bundle.contract_version),
        event_store=event_store,
        audit_log=audit_log,
        non_synthetic_readiness_checker=NonSyntheticReadinessChecker(
            bundle.locked_contract_sha or bundle.contract_version
        ),
    ), event_store, audit_log


def test_non_synthetic_preflight_passes_only_with_complete_approved_metadata(
    runtime_config, non_synthetic_readiness_request: dict
) -> None:
    envelope = {
        "ingestion_mode": "non_synthetic_dry_run_preflight",
        "actor": "synthetic-test-runner",
        "data_flags": {
            "production": False,
            "real_client_data": False,
            "real_matter_data": False,
            "live_connector": False,
        },
        "readiness_request": non_synthetic_readiness_request,
    }

    service, event_store, audit_log = _build_service(runtime_config)
    result = service.ingest(envelope)

    assert result["preflight_ready"] is True
    assert result["stored"] is False
    assert event_store.list_records() == []
    assert audit_log.list_records()[0]["action"] == "dry_run_preflight"


def test_non_synthetic_preflight_fails_closed_when_required_fields_missing(
    runtime_config, non_synthetic_readiness_request: dict
) -> None:
    envelope = {
        "ingestion_mode": "non_synthetic_dry_run_preflight",
        "actor": "synthetic-test-runner",
        "data_flags": {
            "production": False,
            "real_client_data": False,
            "real_matter_data": False,
            "live_connector": False,
        },
        "readiness_request": {
            key: value
            for key, value in non_synthetic_readiness_request.items()
            if key != "allowed_use_basis"
        },
    }

    service, event_store, audit_log = _build_service(runtime_config)
    result = service.ingest(envelope)

    assert result["preflight_ready"] is False
    assert "allowed_use_basis" in result["readiness_result"]["missing"]
    assert event_store.list_records() == []
    assert audit_log.list_records()[0]["result"] == "rejected"


def test_non_synthetic_preflight_fails_closed_when_approval_not_granted(
    runtime_config, non_synthetic_readiness_request: dict
) -> None:
    envelope = {
        "ingestion_mode": "non_synthetic_dry_run_preflight",
        "actor": "synthetic-test-runner",
        "data_flags": {
            "production": False,
            "real_client_data": False,
            "real_matter_data": False,
            "live_connector": False,
        },
        "readiness_request": {
            **non_synthetic_readiness_request,
            "approval_status": "pending_review",
        },
    }

    service, event_store, audit_log = _build_service(runtime_config)
    result = service.ingest(envelope)

    assert result["preflight_ready"] is False
    assert any(
        "approved_for_dry_run" in error
        for error in result["readiness_result"]["errors"]
    )
    assert event_store.list_records() == []
    assert audit_log.list_records()[0]["result"] == "rejected"


def test_non_synthetic_preflight_still_denies_live_connector_or_production_flags(
    runtime_config, non_synthetic_readiness_request: dict
) -> None:
    envelope = {
        "ingestion_mode": "non_synthetic_dry_run_preflight",
        "actor": "synthetic-test-runner",
        "data_flags": {
            "production": False,
            "real_client_data": False,
            "real_matter_data": False,
            "live_connector": True,
        },
        "readiness_request": non_synthetic_readiness_request,
    }

    service, event_store, audit_log = _build_service(runtime_config)
    result = service.ingest(envelope)

    assert result["accepted"] is False
    assert result["stored"] is False
    assert result["policy_result"]["allowed"] is False
    assert event_store.list_records() == []
    assert audit_log.list_records()[0]["details"]["reason"] == "policy_denied"
