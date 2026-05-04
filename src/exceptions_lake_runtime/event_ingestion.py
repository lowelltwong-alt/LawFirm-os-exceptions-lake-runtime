from __future__ import annotations

import copy
from datetime import UTC, datetime
from typing import Any

from .audit_log import AuditLog
from .contract_loader import ContractBundle
from .event_store import EventStore
from .non_synthetic_readiness import NonSyntheticReadinessChecker
from .policy_gateway import PolicyGateway
from .validation_gateway import ValidationGateway


class EventIngestionService:
    """Orchestrate safe synthetic runtime event ingestion."""

    def __init__(
        self,
        contract_bundle: ContractBundle,
        validation_gateway: ValidationGateway,
        policy_gateway: PolicyGateway,
        event_store: EventStore,
        audit_log: AuditLog,
        non_synthetic_readiness_checker: NonSyntheticReadinessChecker,
    ) -> None:
        self.contract_bundle = contract_bundle
        self.validation_gateway = validation_gateway
        self.policy_gateway = policy_gateway
        self.event_store = event_store
        self.audit_log = audit_log
        self.non_synthetic_readiness_checker = non_synthetic_readiness_checker

    def ingest(self, envelope: dict[str, Any]) -> dict[str, Any]:
        ingestion_mode = str(envelope.get("ingestion_mode", "synthetic_test_only"))
        payload = envelope.get("payload", {})
        readiness_request = envelope.get("readiness_request", {})
        event_id = payload.get("exception_id") or readiness_request.get(
            "source_ingestion_manifest_id", "unknown"
        )
        actor = str(envelope.get("actor", "synthetic-test-runner"))
        audit_action = (
            "dry_run_preflight"
            if ingestion_mode == "non_synthetic_dry_run_preflight"
            else "ingest_synthetic_event"
        )

        policy_result = self.policy_gateway.evaluate(envelope).to_dict()
        if not policy_result["allowed"]:
            self._append_audit_record(
                action=audit_action,
                result="rejected",
                event_id=event_id,
                actor=actor,
                details={"reason": "policy_denied", "policy_result": policy_result},
            )
            return {
                "accepted": False,
                "stored": False,
                "event_id": event_id,
                "contract_version": self.contract_bundle.contract_version,
                "policy_result": policy_result,
                "validation_result": None,
            }

        if ingestion_mode == "non_synthetic_dry_run_preflight":
            readiness_result = self.non_synthetic_readiness_checker.evaluate(
                copy.deepcopy(readiness_request)
            ).to_dict()
            self._append_audit_record(
                action="dry_run_preflight",
                result="accepted" if readiness_result["ready"] else "rejected",
                event_id=event_id,
                actor=actor,
                details={
                    "reason": (
                        "preflight_ready"
                        if readiness_result["ready"]
                        else "preflight_not_ready"
                    ),
                    "readiness_result": readiness_result,
                    "policy_result": policy_result,
                },
            )
            return {
                "accepted": False,
                "stored": False,
                "preflight_ready": readiness_result["ready"],
                "event_id": event_id,
                "contract_version": self.contract_bundle.contract_version,
                "policy_result": policy_result,
                "validation_result": None,
                "readiness_result": readiness_result,
                "mode": "non_synthetic_dry_run_preflight",
            }

        validation_result = self.validation_gateway.validate_exception_event(
            copy.deepcopy(payload)
        ).to_dict()
        if not validation_result["valid"]:
            self._append_audit_record(
                action=audit_action,
                result="rejected",
                event_id=event_id,
                actor=actor,
                details={
                    "reason": "validation_failed",
                    "validation_result": validation_result,
                },
            )
            return {
                "accepted": False,
                "stored": False,
                "event_id": event_id,
                "contract_version": self.contract_bundle.contract_version,
                "policy_result": policy_result,
                "validation_result": validation_result,
            }

        event_record = {
            "record_type": "synthetic_exception_event",
            "event_id": event_id,
            "received_at": self._timestamp(),
            "contract_version": self.contract_bundle.contract_version,
            "schema_id": validation_result["schema_id"],
            "validation_result": validation_result,
            "policy_result": policy_result,
            "payload": copy.deepcopy(payload),
        }
        self.event_store.append(event_record)

        self._append_audit_record(
            action=audit_action,
            result="accepted",
            event_id=event_id,
            actor=actor,
            details={"reason": "stored"},
        )

        return {
            "accepted": True,
            "stored": True,
            "event_id": event_id,
            "contract_version": self.contract_bundle.contract_version,
            "policy_result": policy_result,
            "validation_result": validation_result,
        }

    def _append_audit_record(
        self,
        *,
        action: str,
        result: str,
        event_id: str,
        actor: str,
        details: dict[str, Any],
    ) -> None:
        self.audit_log.append(
            {
                "timestamp": self._timestamp(),
                "action": action,
                "result": result,
                "event_id": event_id,
                "actor": actor,
                "contract_version": self.contract_bundle.contract_version,
                "details": details,
            }
        )

    @staticmethod
    def _timestamp() -> str:
        return datetime.now(tz=UTC).isoformat().replace("+00:00", "Z")
