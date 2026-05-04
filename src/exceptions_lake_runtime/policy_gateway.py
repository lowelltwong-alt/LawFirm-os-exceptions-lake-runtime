from __future__ import annotations

from dataclasses import dataclass
from typing import Any


REQUIRED_DATA_FLAGS = (
    "production",
    "real_client_data",
    "real_matter_data",
    "live_connector",
)


@dataclass(frozen=True)
class PolicyDecision:
    allowed: bool
    reason: str
    contract_version: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "allowed": self.allowed,
            "reason": self.reason,
            "contract_version": self.contract_version,
        }


class PolicyGateway:
    """Enforce a deny-by-default posture for synthetic-only MVP ingestion."""

    def __init__(self, contract_version: str) -> None:
        self.contract_version = contract_version

    def evaluate(self, envelope: dict[str, Any]) -> PolicyDecision:
        ingestion_mode = envelope.get("ingestion_mode")
        if ingestion_mode == "synthetic_test_only":
            return self._evaluate_synthetic_ingestion(envelope)
        if ingestion_mode == "non_synthetic_dry_run_preflight":
            return self._evaluate_non_synthetic_preflight(envelope)
        return self._deny("unsupported_ingestion_mode")

    def _evaluate_synthetic_ingestion(self, envelope: dict[str, Any]) -> PolicyDecision:
        data_flags = envelope.get("data_flags")
        if not isinstance(data_flags, dict):
            return self._deny("data_flags_required")

        for flag_name in REQUIRED_DATA_FLAGS:
            flag_value = data_flags.get(flag_name)
            if flag_value is not False:
                return self._deny(f"{flag_name}_must_be_false")

        if not isinstance(envelope.get("payload"), dict):
            return self._deny("payload_must_be_object")

        return PolicyDecision(
            allowed=True,
            reason="synthetic_test_only_allowed",
            contract_version=self.contract_version,
        )

    def _evaluate_non_synthetic_preflight(
        self, envelope: dict[str, Any]
    ) -> PolicyDecision:
        data_flags = envelope.get("data_flags")
        if not isinstance(data_flags, dict):
            return self._deny("data_flags_required")

        for flag_name in REQUIRED_DATA_FLAGS:
            flag_value = data_flags.get(flag_name)
            if flag_value is not False:
                return self._deny(f"{flag_name}_must_be_false")

        if "payload" in envelope and envelope.get("payload") not in (None, {}):
            return self._deny("non_synthetic_payload_ingestion_not_allowed")

        readiness_request = envelope.get("readiness_request")
        if not isinstance(readiness_request, dict):
            return self._deny("readiness_request_required")

        return PolicyDecision(
            allowed=True,
            reason="non_synthetic_dry_run_preflight_allowed",
            contract_version=self.contract_version,
        )

    def _deny(self, reason: str) -> PolicyDecision:
        return PolicyDecision(
            allowed=False,
            reason=reason,
            contract_version=self.contract_version,
        )
