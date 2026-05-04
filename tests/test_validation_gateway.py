from __future__ import annotations

import copy

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
    assert any("event_class does not match" in error for error in result.errors)


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
