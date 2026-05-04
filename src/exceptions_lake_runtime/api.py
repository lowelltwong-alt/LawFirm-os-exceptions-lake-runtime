from __future__ import annotations

from typing import Any

from .audit_log import AuditLog
from .config import RuntimeConfig
from .contract_loader import ContractLoader
from .event_ingestion import EventIngestionService
from .event_store import EventStore
from .non_synthetic_readiness import NonSyntheticReadinessChecker
from .policy_gateway import PolicyGateway
from .pressure_builder import PressureBuilder
from .validation_gateway import ValidationGateway


def _build_runtime_services(config: RuntimeConfig | None = None) -> dict[str, Any]:
    resolved_config = config or RuntimeConfig.from_env()
    contract_bundle = ContractLoader().load(resolved_config)
    validation_gateway = ValidationGateway(contract_bundle)
    policy_gateway = PolicyGateway(contract_bundle.contract_version)
    event_store = EventStore(resolved_config.event_store_path)
    audit_log = AuditLog(resolved_config.audit_log_path)
    readiness_checker = NonSyntheticReadinessChecker(
        contract_bundle.locked_contract_sha or contract_bundle.contract_version
    )
    ingestion_service = EventIngestionService(
        contract_bundle=contract_bundle,
        validation_gateway=validation_gateway,
        policy_gateway=policy_gateway,
        event_store=event_store,
        audit_log=audit_log,
        non_synthetic_readiness_checker=readiness_checker,
    )
    return {
        "config": resolved_config,
        "contract_bundle": contract_bundle,
        "event_store": event_store,
        "audit_log": audit_log,
        "ingestion_service": ingestion_service,
    }


def health(config: RuntimeConfig | None = None) -> dict[str, Any]:
    try:
        services = _build_runtime_services(config=config)
    except Exception as exc:  # pragma: no cover - exercised through integration use
        return {
            "ok": False,
            "runtime_status": "not_ready",
            "contract_repo_available": False,
            "contract_version": None,
            "locked_contract_sha": None,
            "non_production": True,
            "detail": str(exc),
        }

    contract_bundle = services["contract_bundle"]
    return {
        "ok": True,
        "runtime_status": "ready",
        "contract_repo_available": True,
        "contract_version": contract_bundle.contract_version,
        "locked_contract_sha": contract_bundle.locked_contract_sha,
        "export_manifest_present": contract_bundle.export_manifest_present,
        "non_production": True,
    }


def ingest_synthetic_event(
    envelope: dict[str, Any], config: RuntimeConfig | None = None
) -> dict[str, Any]:
    services = _build_runtime_services(config=config)
    return services["ingestion_service"].ingest(envelope)


def list_events(config: RuntimeConfig | None = None) -> list[dict[str, Any]]:
    services = _build_runtime_services(config=config)
    return services["event_store"].list_records()


def build_synthetic_envelope(
    payload: dict[str, Any], actor: str = "synthetic-test-runner"
) -> dict[str, Any]:
    return {
        "ingestion_mode": "synthetic_test_only",
        "actor": actor,
        "data_flags": {
            "production": False,
            "real_client_data": False,
            "real_matter_data": False,
            "live_connector": False,
        },
        "payload": payload,
    }


def build_non_synthetic_preflight_envelope(
    readiness_request: dict[str, Any], actor: str = "synthetic-test-runner"
) -> dict[str, Any]:
    return {
        "ingestion_mode": "non_synthetic_dry_run_preflight",
        "actor": actor,
        "data_flags": {
            "production": False,
            "real_client_data": False,
            "real_matter_data": False,
            "live_connector": False,
        },
        "readiness_request": readiness_request,
    }


def build_pressure_candidate(config: RuntimeConfig | None = None) -> dict[str, Any]:
    services = _build_runtime_services(config=config)
    builder = PressureBuilder(
        services["contract_bundle"], event_store=services["event_store"]
    )
    return builder.build_candidate()


def run_non_synthetic_preflight(
    envelope: dict[str, Any], config: RuntimeConfig | None = None
) -> dict[str, Any]:
    services = _build_runtime_services(config=config)
    return services["ingestion_service"].ingest(envelope)
