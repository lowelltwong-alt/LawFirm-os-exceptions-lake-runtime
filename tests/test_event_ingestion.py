from __future__ import annotations

import copy
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

# Ensure tests load local in-repo modules.
for module_name in (
    "exceptions_lake_runtime",
    "exceptions_lake_runtime.audit_log",
    "exceptions_lake_runtime.contract_loader",
    "exceptions_lake_runtime.event_ingestion",
    "exceptions_lake_runtime.event_store",
    "exceptions_lake_runtime.non_synthetic_readiness",
    "exceptions_lake_runtime.policy_gateway",
    "exceptions_lake_runtime.validation_gateway",
):
    sys.modules.pop(module_name, None)

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


def test_valid_synthetic_envelope_is_accepted_and_stored(
    runtime_config, synthetic_envelope: dict
) -> None:
    service, event_store, audit_log = _build_service(runtime_config)

    result = service.ingest(synthetic_envelope)

    assert result["accepted"] is True
    assert result["stored"] is True
    assert len(event_store.list_records()) == 1
    assert len(audit_log.list_records()) == 1
    assert audit_log.list_records()[0]["result"] == "accepted"


def test_invalid_payload_is_rejected_and_not_stored(
    runtime_config, synthetic_envelope: dict
) -> None:
    invalid_envelope = copy.deepcopy(synthetic_envelope)
    invalid_envelope["payload"].pop("summary")

    service, event_store, audit_log = _build_service(runtime_config)
    result = service.ingest(invalid_envelope)

    assert result["accepted"] is False
    assert result["stored"] is False
    assert event_store.list_records() == []
    assert len(audit_log.list_records()) == 1
    assert audit_log.list_records()[0]["details"]["reason"] == "validation_failed"
    assert result["validation_result"]["schema_id"] == "exception-event-v1"


def test_route_event_class_mismatch_preserves_validation_metadata_in_audit(
    runtime_config, synthetic_envelope: dict
) -> None:
    invalid_envelope = copy.deepcopy(synthetic_envelope)
    invalid_envelope["payload"]["event_class"] = "workflow_escalation"

    service, event_store, audit_log = _build_service(runtime_config)
    result = service.ingest(invalid_envelope)

    assert result["accepted"] is False
    assert result["stored"] is False
    assert event_store.list_records() == []
    assert result["validation_result"]["schema_id"] == "exception-event-v1"
    assert any(
        "event_class does not match canonical route registry" in error
        for error in result["validation_result"]["errors"]
    )
    assert len(audit_log.list_records()) == 1
    audit_validation = audit_log.list_records()[0]["details"]["validation_result"]
    assert audit_validation["schema_id"] == "exception-event-v1"
    assert any(
        "event_class does not match canonical route registry" in error
        for error in audit_validation["errors"]
    )


def test_policy_denied_envelope_is_rejected_and_not_stored(
    runtime_config, synthetic_envelope: dict
) -> None:
    denied_envelope = copy.deepcopy(synthetic_envelope)
    denied_envelope["data_flags"]["production"] = True

    service, event_store, audit_log = _build_service(runtime_config)
    result = service.ingest(denied_envelope)

    assert result["accepted"] is False
    assert result["stored"] is False
    assert event_store.list_records() == []
    assert len(audit_log.list_records()) == 1
    assert audit_log.list_records()[0]["details"]["reason"] == "policy_denied"


def test_each_ingest_emits_audit_records(runtime_config, synthetic_envelope: dict) -> None:
    service, event_store, audit_log = _build_service(runtime_config)

    accepted = service.ingest(synthetic_envelope)
    rejected = service.ingest(
        {
            **synthetic_envelope,
            "data_flags": {
                "production": True,
                "real_client_data": False,
                "real_matter_data": False,
                "live_connector": False,
            },
        }
    )

    assert accepted["accepted"] is True
    assert rejected["accepted"] is False
    assert len(event_store.list_records()) == 1
    assert [record["result"] for record in audit_log.list_records()] == [
        "accepted",
        "rejected",
    ]
