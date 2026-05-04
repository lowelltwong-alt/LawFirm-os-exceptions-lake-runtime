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
    "exceptions_lake_runtime.contract_loader",
    "exceptions_lake_runtime.validation_gateway",
):
    sys.modules.pop(module_name, None)

from exceptions_lake_runtime.contract_loader import ContractLoader
from exceptions_lake_runtime.validation_gateway import ValidationGateway


def test_accepts_valid_synthetic_exception_event(
    runtime_config,
    synthetic_event: dict,
) -> None:
    bundle = ContractLoader().load(runtime_config)
    result = ValidationGateway(bundle).validate_exception_event(synthetic_event)

    assert result.valid is True
    assert result.errors == []
    assert result.route_registry_checked is True


def test_rejects_malformed_payload(runtime_config, synthetic_event: dict) -> None:
    invalid_payload = copy.deepcopy(synthetic_event)
    invalid_payload.pop("summary")

    bundle = ContractLoader().load(runtime_config)
    result = ValidationGateway(bundle).validate_exception_event(invalid_payload)

    assert result.valid is False
    assert any("summary" in error for error in result.errors)


def test_rejects_unknown_route_id(runtime_config, synthetic_event: dict) -> None:
    invalid_payload = copy.deepcopy(synthetic_event)
    invalid_payload["route"]["route_id"] = "route.unknown.v1"

    bundle = ContractLoader().load(runtime_config)
    result = ValidationGateway(bundle).validate_exception_event(invalid_payload)

    assert result.valid is False
    assert any("unknown route_id" in error for error in result.errors)


def test_rejects_route_event_class_mismatch(
    runtime_config, synthetic_event: dict
) -> None:
    invalid_payload = copy.deepcopy(synthetic_event)
    invalid_payload["event_class"] = "workflow_escalation"

    bundle = ContractLoader().load(runtime_config)
    result = ValidationGateway(bundle).validate_exception_event(invalid_payload)

    assert result.valid is False
    assert any(
        "event_class does not match canonical route registry" in error
        for error in result.errors
    )


def test_rejects_unknown_event_class(runtime_config, synthetic_event: dict) -> None:
    invalid_payload = copy.deepcopy(synthetic_event)
    invalid_payload["event_class"] = "unknown_event_class"

    bundle = ContractLoader().load(runtime_config)
    result = ValidationGateway(bundle).validate_exception_event(invalid_payload)

    assert result.valid is False
    assert result.schema_id == "exception-event-v1"
    assert any("unknown event_class" in error for error in result.errors)


def test_rejects_direct_mutation_attempts(
    runtime_config, synthetic_event: dict
) -> None:
    invalid_payload = copy.deepcopy(synthetic_event)
    invalid_payload["canonical_mutation_control"]["direct_mutation_attempted"] = True

    bundle = ContractLoader().load(runtime_config)
    result = ValidationGateway(bundle).validate_exception_event(invalid_payload)

    assert result.valid is False
    assert any(
        "direct_mutation_attempted" in error or "False was expected" in error
        for error in result.errors
    )
