from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator
from jsonschema.validators import RefResolver

from .contract_loader import ContractBundle

EXCEPTION_EVENT_SCHEMA_ID = "exception-event-v1"


@dataclass(frozen=True)
class ValidationResult:
    valid: bool
    errors: list[str]
    schema_id: str
    schema_path: str
    contract_version: str
    route_registry_checked: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "valid": self.valid,
            "errors": list(self.errors),
            "schema_id": self.schema_id,
            "schema_path": self.schema_path,
            "contract_version": self.contract_version,
            "route_registry_checked": self.route_registry_checked,
        }


class ValidationGateway:
    """Validate runtime payloads against contract repo schemas and route rules."""

    def __init__(self, contract_bundle: ContractBundle) -> None:
        self.contract_bundle = contract_bundle
        self.schema_path = contract_bundle.schema_paths[EXCEPTION_EVENT_SCHEMA_ID]
        self.schema = json.loads(self.schema_path.read_text(encoding="utf-8"))
        self.schema_store = self._build_schema_store(self.schema_path.parent)
        self.validator = Draft202012Validator(
            self.schema,
            resolver=RefResolver(
                base_uri=self.schema_path.resolve().as_uri(),
                referrer=self.schema,
                store=self.schema_store,
            ),
            format_checker=Draft202012Validator.FORMAT_CHECKER,
        )
        self.route_map = {
            route["route_id"]: route
            for route in contract_bundle.route_registry.get("routes", [])
            if isinstance(route, dict) and "route_id" in route
        }

    def validate_exception_event(self, payload: dict[str, Any]) -> ValidationResult:
        errors = self._collect_schema_errors(payload)
        route_registry_checked = False

        if not errors:
            route_registry_checked = True
            errors.extend(self._collect_route_errors(payload))

        return ValidationResult(
            valid=not errors,
            errors=errors,
            schema_id=EXCEPTION_EVENT_SCHEMA_ID,
            schema_path=str(self.schema_path),
            contract_version=self.contract_bundle.contract_version,
            route_registry_checked=route_registry_checked,
        )

    def _collect_schema_errors(self, payload: dict[str, Any]) -> list[str]:
        validation_errors = sorted(
            self.validator.iter_errors(payload),
            key=lambda error: list(error.path),
        )
        messages = []
        for error in validation_errors:
            location = ".".join(str(part) for part in error.path) or "<root>"
            messages.append(f"{location}: {error.message}")
        return messages

    def _collect_route_errors(self, payload: dict[str, Any]) -> list[str]:
        errors: list[str] = []
        route = payload.get("route", {})
        origin = payload.get("origin", {})
        mutation = payload.get("canonical_mutation_control", {})

        route_id = route.get("route_id")
        route_entry = self.route_map.get(route_id)
        if route_entry is None:
            return [f"route.route_id: unknown route_id '{route_id}'."]

        event_class = payload.get("event_class")
        if event_class != route_entry.get("event_class"):
            errors.append(
                "event_class does not match the configured route registry event_class."
            )

        if route.get("destination_loop") != route_entry.get("destination_loop"):
            errors.append(
                "route.destination_loop does not match the configured route registry."
            )

        if route.get("promotion_gate_required") != route_entry.get(
            "promotion_gate_required"
        ):
            errors.append(
                "route.promotion_gate_required does not match the configured route registry."
            )

        allowed_source_layers = route_entry.get("allowed_source_layers", [])
        if origin.get("layer") not in allowed_source_layers:
            errors.append("origin.layer is not allowed for the selected route.")

        if mutation.get("direct_mutation_attempted") is not False:
            errors.append(
                "canonical_mutation_control.direct_mutation_attempted must be false."
            )

        allowed_actions = route_entry.get("allowed_raw_actions", [])
        if mutation.get("allowed_action") not in allowed_actions:
            errors.append(
                "canonical_mutation_control.allowed_action is not allowed for the selected route."
            )

        return errors

    @staticmethod
    def _build_schema_store(schema_root: Path) -> dict[str, Any]:
        store: dict[str, Any] = {}
        for schema_file in schema_root.rglob("*.json"):
            try:
                document = json.loads(schema_file.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                continue
            store[schema_file.resolve().as_uri()] = document
            schema_id = document.get("$id")
            if isinstance(schema_id, str) and schema_id:
                store[schema_id] = document
        return store
