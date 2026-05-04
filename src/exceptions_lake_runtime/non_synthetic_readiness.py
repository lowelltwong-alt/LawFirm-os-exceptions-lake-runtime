from __future__ import annotations

from dataclasses import dataclass
from typing import Any

REQUIRED_STRING_FIELDS = (
    "source_name",
    "source_system_type",
    "source_ingestion_manifest_id",
    "data_classification",
    "sensitivity_level",
    "allowed_use_basis",
    "retention_rule",
    "access_owner",
    "business_owner",
    "validation_owner",
    "approval_status",
    "rollback_or_quarantine_plan",
    "contract_sha",
)

NON_CLAIMS = [
    "no production runtime",
    "no real events",
    "no real connectors",
    "no dashboards",
    "no canon mutation",
    "non-synthetic dry run does not permit real ingestion",
]


@dataclass(frozen=True)
class NonSyntheticReadinessResult:
    ready: bool
    mode: str
    missing: list[str]
    errors: list[str]
    warnings: list[str]
    non_claims: list[str]

    def to_dict(self) -> dict[str, Any]:
        return {
            "ready": self.ready,
            "mode": self.mode,
            "missing": list(self.missing),
            "errors": list(self.errors),
            "warnings": list(self.warnings),
            "non_claims": list(self.non_claims),
        }


class NonSyntheticReadinessChecker:
    """Preflight checker for future non-synthetic data admission."""

    def __init__(self, expected_contract_sha: str) -> None:
        self.expected_contract_sha = expected_contract_sha

    def evaluate(self, request: dict[str, Any]) -> NonSyntheticReadinessResult:
        missing: list[str] = []
        errors: list[str] = []
        warnings = [
            "dry_run_only_preflight_does_not_ingest_or_persist_non_synthetic_data",
            "first_live_connector_and_real_data_admission_require_a_later_pr",
        ]

        for field_name in REQUIRED_STRING_FIELDS:
            field_value = request.get(field_name)
            if not isinstance(field_value, str) or not field_value.strip():
                missing.append(field_name)

        manifest_path = request.get("source_ingestion_manifest_path")
        manifest_ref = request.get("source_ingestion_manifest_ref")
        if not isinstance(manifest_path, str) and not isinstance(manifest_ref, str):
            missing.append("source_ingestion_manifest_path_or_ref")
        elif not (str(manifest_path or "").strip() or str(manifest_ref or "").strip()):
            missing.append("source_ingestion_manifest_path_or_ref")

        if request.get("evidence_provenance_available") is not True:
            if "evidence_provenance_available" not in missing:
                missing.append("evidence_provenance_available")

        if request.get("dry_run_only") is not True:
            if "dry_run_only" not in missing:
                missing.append("dry_run_only")

        approval_status = request.get("approval_status")
        if approval_status != "approved_for_dry_run":
            errors.append("approval_status must be approved_for_dry_run.")

        if request.get("dry_run_only") is not True:
            errors.append("dry_run_only must be true.")

        if request.get("evidence_provenance_available") is not True:
            errors.append("evidence_provenance_available must be true.")

        contract_sha = request.get("contract_sha")
        if isinstance(contract_sha, str) and contract_sha.strip():
            if contract_sha != self.expected_contract_sha:
                errors.append(
                    "contract_sha does not match the runtime's currently pinned contract SHA."
                )

        return NonSyntheticReadinessResult(
            ready=not missing and not errors,
            mode="dry_run_only",
            missing=sorted(dict.fromkeys(missing)),
            errors=errors,
            warnings=warnings,
            non_claims=list(NON_CLAIMS),
        )
