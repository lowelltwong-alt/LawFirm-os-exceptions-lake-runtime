from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from .contract_loader import ContractBundle
from .event_store import EventStore


VECTOR_CLASS_BY_EVENT_CLASS = {
    "retrieval_miss": "retrieval_quality_pressure",
    "workflow_escalation": "workflow_friction_pressure",
    "authority_conflict_override": "authority_policy_pressure",
}


class PressureBuilder:
    """Build a synthetic pressure-vector candidate from accepted synthetic events."""

    def __init__(
        self,
        contract_bundle: ContractBundle,
        event_store: EventStore | None = None,
    ) -> None:
        self.contract_bundle = contract_bundle
        self.event_store = event_store
        self.route_map = {
            route["route_id"]: route
            for route in contract_bundle.route_registry.get("routes", [])
            if isinstance(route, dict) and "route_id" in route
        }

    def build_candidate(
        self, event_records: list[dict[str, Any]] | None = None
    ) -> dict[str, Any]:
        if event_records is None:
            if self.event_store is None:
                raise ValueError("event_store is required when event_records are not supplied.")
            event_records = self.event_store.list_records()

        accepted_records = [
            record
            for record in event_records
            if record.get("policy_result", {}).get("allowed") is True
            and record.get("validation_result", {}).get("valid") is True
        ]
        if not accepted_records:
            raise ValueError("No accepted synthetic exception events are available.")

        payloads = [record["payload"] for record in accepted_records]
        event_classes = {payload["event_class"] for payload in payloads}
        if len(event_classes) == 1:
            vector_class = VECTOR_CLASS_BY_EVENT_CLASS[next(iter(event_classes))]
        else:
            vector_class = "cross_loop_pressure"

        recommended_route_ids = sorted(
            {payload["route"]["route_id"] for payload in payloads}
        )
        source_layers = sorted({payload["origin"]["layer"] for payload in payloads})

        follow_on_families = sorted(
            {
                family
                for route_id in recommended_route_ids
                for family in self.route_map.get(route_id, {}).get(
                    "allowed_follow_on_families", []
                )
                if family in {"adaptation-proposal", "opportunity-object"}
            }
        )

        first_event_suffix = payloads[0]["exception_id"].split("-", maxsplit=1)[1]
        pressure_vector = {
            "pressure_vector_id": f"PV-{first_event_suffix}",
            "schema_type": "pressure-vector",
            "schema_version": "v1",
            "vector_class": vector_class,
            "derived_from_exception_ids": [
                payload["exception_id"] for payload in payloads
            ],
            "source_layers": source_layers,
            "signal_strength": min(1.0, round(0.25 * len(payloads), 2)),
            "recommended_route_ids": recommended_route_ids,
            "suggested_follow_on_families": follow_on_families,
            "review_status": "draft",
            "created_at": self._timestamp(),
            "notes": "synthetic_candidate_only_not_canonical",
            "mutation_boundary": {
                "no_direct_canonical_mutation": True,
                "promotion_decision_required_for_canonical_change": True,
            },
        }

        return {
            "candidate_status": "synthetic_candidate_not_canonical",
            "contract_version": self.contract_bundle.contract_version,
            "pressure_vector": pressure_vector,
        }

    @staticmethod
    def _timestamp() -> str:
        return datetime.now(tz=UTC).isoformat().replace("+00:00", "Z")
