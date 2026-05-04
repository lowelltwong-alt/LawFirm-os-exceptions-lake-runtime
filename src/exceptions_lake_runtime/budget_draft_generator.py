from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

from .budget_template_rows import (
    BUDGET_COLUMNS,
    INSTRUCTION_NOTE,
    ROW_CODE_TO_LABEL,
    ROW_CODE_TO_PHASE_CODE,
    SUMMARY_LABELS,
    TEMPLATE_FOOTER_NOTE,
    TEMPLATE_PHASE_SECTIONS,
    TEMPLATE_TITLE,
    ZERO_ROW_NOTE,
    build_template_phase_sections,
    expand_emphasis_refs,
)
from .contract_loader import ContractBundle

VIEW_BUDGET_SCHEMA_ID = "view-budget-workbook-v1"
BASE_ROW_WEIGHTS = {
    "L110": 2.0,
    "L120": 1.9,
    "L130": 0.6,
    "L140": 0.5,
    "L150": 1.0,
    "L160": 0.7,
    "L210": 0.8,
    "L230": 0.3,
    "L240": 0.5,
    "L250": 0.2,
    "L310": 1.8,
    "L320": 1.5,
    "L330": 1.0,
    "L340": 0.7,
    "L350": 0.4,
    "L410": 0.3,
    "L420": 0.3,
    "L430": 0.2,
    "L440": 0.2,
    "L450": 0.2,
    "L460": 0.1,
    "L470": 0.1,
    "L510": 0.1,
    "L520": 0.1,
    "L530": 0.1,
    "E101": 0.1,
    "E103": 0.1,
    "E105": 0.1,
    "E106": 0.3,
    "E107": 0.05,
    "E108": 0.05,
    "E109": 0.1,
    "E112": 0.2,
    "E115": 0.3,
    "E118": 0.2,
    "E119": 0.4,
}
PHASE_BILLED_PROGRESS_DEFAULTS = {
    "pre_suit": {"L100": 0.25, "L200": 0.05, "L300": 0.0, "L400": 0.0, "L500": 0.0, "E100": 0.05},
    "pleadings": {"L100": 0.35, "L200": 0.2, "L300": 0.05, "L400": 0.0, "L500": 0.0, "E100": 0.08},
    "written_discovery": {"L100": 0.4, "L200": 0.25, "L300": 0.18, "L400": 0.0, "L500": 0.0, "E100": 0.12},
    "depositions": {"L100": 0.45, "L200": 0.25, "L300": 0.35, "L400": 0.02, "L500": 0.0, "E100": 0.15},
    "expert": {"L100": 0.45, "L200": 0.3, "L300": 0.45, "L400": 0.05, "L500": 0.0, "E100": 0.2},
    "mediation": {"L100": 0.5, "L200": 0.3, "L300": 0.5, "L400": 0.08, "L500": 0.0, "E100": 0.22},
    "trial_prep": {"L100": 0.5, "L200": 0.35, "L300": 0.55, "L400": 0.2, "L500": 0.0, "E100": 0.24},
}
NON_CLAIMS = [
    "synthetic placeholder amounts only",
    "no production budget accuracy claimed",
    "no real FMG data or real matters",
    "no canonical mutation from this draft",
]
ROW_TRIGGER_MAP = {
    "missing_required_budget_driver": ["L150"],
    "budget_phase_missing": ["L150"],
    "budget_exceeds_synthetic_threshold": ["L150"],
    "staffing_mix_outside_expected_pattern": ["L120", "L150"],
    "expert_need_not_reflected_in_L130_L340_E119": ["L130", "L340", "E119"],
    "deposition_burden_not_reflected_in_L330_E115": ["L330", "E115"],
    "trial_likelihood_not_reflected_in_L400": ["L410", "L420", "L430", "L440", "L450", "L460", "L470"],
    "appeal_likelihood_not_reflected_in_L500": ["L510", "L520", "L530"],
    "amount_billed_to_date_incompatible_with_remaining_budget": ["L150"],
    "synthetic_guideline_lookup_miss": ["L120", "L150"],
}
REVIEW_PATH_BY_TRIGGER = {
    "synthetic_guideline_lookup_miss": "knowledge_owner_review_and_retrieval_tuning_opportunity_candidate",
    "missing_required_budget_driver": "budget_ops_review_and_workflow_redesign_candidate",
    "budget_phase_missing": "budget_ops_and_billing_integrity_review",
    "budget_exceeds_synthetic_threshold": "billing_integrity_review",
    "staffing_mix_outside_expected_pattern": "billing_integrity_review",
    "expert_need_not_reflected_in_L130_L340_E119": "billing_integrity_review",
    "deposition_burden_not_reflected_in_L330_E115": "billing_integrity_review",
    "trial_likelihood_not_reflected_in_L400": "billing_integrity_and_workflow_review",
    "appeal_likelihood_not_reflected_in_L500": "billing_integrity_review",
    "amount_billed_to_date_incompatible_with_remaining_budget": "billing_integrity_and_workflow_review",
}


class BudgetDraftGenerator:
    def __init__(self, contract_bundle: ContractBundle) -> None:
        self.contract_bundle = contract_bundle
        self.schema_path = self._resolve_schema_path(contract_bundle.contract_repo_root)
        self.schema = json.loads(self.schema_path.read_text(encoding="utf-8"))
        self.validator = Draft202012Validator(self.schema)

    def generate(
        self,
        case: dict[str, Any],
        classifications: dict[str, Any],
        detected_exceptions: list[dict[str, Any]],
        *,
        ingested_event_ids: list[str] | None = None,
        pressure_candidate_status: str | None = None,
    ) -> dict[str, Any]:
        row_allocations = self._build_row_allocations(case, classifications)
        row_exception_refs = self._build_row_exception_refs(detected_exceptions)
        phase_sections = self._build_phase_sections(
            row_allocations=row_allocations,
            row_exception_refs=row_exception_refs,
        )
        totals = self._compute_totals(phase_sections)
        draft = {
            "schema_id": VIEW_BUDGET_SCHEMA_ID,
            "schema_type": "view-budget-workbook",
            "schema_version": "draft-v1",
            "budget_draft_id": self._budget_draft_id(case["case_id"]),
            "candidate_status": "synthetic_candidate_not_canonical",
            "contract_version": self.contract_bundle.locked_contract_sha
            or self.contract_bundle.contract_version,
            "template_title": TEMPLATE_TITLE,
            "instruction_note": INSTRUCTION_NOTE,
            "budget_columns": list(BUDGET_COLUMNS),
            "matter_header": self._build_matter_header(case),
            "phase_sections": phase_sections,
            "totals": totals,
            "summary": {
                "original_budget_label": SUMMARY_LABELS["original_budget_label"],
                "original_budget_value": totals["original_total_budgeted_amount"],
                "updated_budget_label": SUMMARY_LABELS["updated_budget_label"],
                "updated_budget_value": totals["new_total_budgeted_amount"],
            },
            "template_footer_note": TEMPLATE_FOOTER_NOTE,
            "learning_metadata": {
                "detected_exception_triggers": [
                    item["trigger"] for item in detected_exceptions
                ],
                "ingested_event_ids": list(ingested_event_ids or []),
                "pressure_candidate_status": pressure_candidate_status,
                "review_packet_required": bool(detected_exceptions),
                "review_path": self._review_path(detected_exceptions),
                "refusal_reason": None,
            },
            "non_claims": list(NON_CLAIMS),
        }
        errors = self.validate(draft)
        if errors:
            raise ValueError(
                "Generated budget draft does not validate against "
                f"{VIEW_BUDGET_SCHEMA_ID}: {'; '.join(errors)}"
            )
        return draft

    def validate(self, draft: dict[str, Any]) -> list[str]:
        errors = sorted(self.validator.iter_errors(draft), key=lambda error: list(error.path))
        messages: list[str] = []
        for error in errors:
            location = ".".join(str(part) for part in error.path) or "<root>"
            messages.append(f"{location}: {error.message}")
        return messages

    def _build_row_allocations(
        self, case: dict[str, Any], classifications: dict[str, Any]
    ) -> dict[str, dict[str, float | list[str]]]:
        budget_profile = case.get("budget_profile", {})
        original_total = float(budget_profile.get("synthetic_original_total", 18000.0))
        update_adjustment_total = float(
            budget_profile.get("synthetic_update_adjustment_total", 0.0)
        )
        phase_progress = PHASE_BILLED_PROGRESS_DEFAULTS.get(
            classifications["litigation_phase"],
            PHASE_BILLED_PROGRESS_DEFAULTS["written_discovery"],
        )
        emphasis_rows = expand_emphasis_refs(classifications["row_emphasis"])
        gap_rows = expand_emphasis_refs(list(budget_profile.get("synthetic_gap_refs", [])))
        update_rows = expand_emphasis_refs(
            list(budget_profile.get("synthetic_update_priority_refs", []))
        ) or emphasis_rows

        weights: dict[str, float] = {}
        for row_code in ROW_CODE_TO_LABEL:
            weight = BASE_ROW_WEIGHTS.get(row_code, 0.0)
            if row_code in emphasis_rows:
                weight += 1.2
            if row_code in gap_rows:
                weight *= 0.15
            weights[row_code] = max(weight, 0.0)

        total_weight = sum(weight for weight in weights.values() if weight > 0)
        allocations: dict[str, dict[str, float | list[str]]] = {}
        for row_code in ROW_CODE_TO_LABEL:
            weight = weights[row_code]
            if total_weight <= 0 or weight <= 0:
                original_amount = 0.0
            else:
                original_amount = self._round_amount(original_total * weight / total_weight)

            phase_code = ROW_CODE_TO_PHASE_CODE[row_code]
            billed_amount = self._round_amount(original_amount * phase_progress.get(phase_code, 0.0))
            remaining_amount = self._round_amount(max(original_amount - billed_amount, 0.0))
            new_amount = original_amount
            if row_code in update_rows and update_adjustment_total > 0:
                new_amount = self._round_amount(
                    new_amount + update_adjustment_total / max(len(update_rows), 1)
                )

            driver_refs = [ref for ref in classifications["row_emphasis"] if row_code in expand_emphasis_refs([ref])]
            allocations[row_code] = {
                "original_budgeted_amount": original_amount,
                "amount_billed_to_date": billed_amount,
                "original_budget_amount_remaining": remaining_amount,
                "new_budgeted_amount": new_amount,
                "driver_refs": driver_refs,
            }

        overrides = budget_profile.get("row_amount_overrides", {})
        for row_code, values in overrides.items():
            if row_code not in allocations or not isinstance(values, dict):
                continue
            for key in (
                "original_budgeted_amount",
                "amount_billed_to_date",
                "original_budget_amount_remaining",
                "new_budgeted_amount",
            ):
                if key in values:
                    allocations[row_code][key] = self._round_amount(float(values[key]))
        return allocations

    def _build_phase_sections(
        self,
        *,
        row_allocations: dict[str, dict[str, float | list[str]]],
        row_exception_refs: dict[str, list[str]],
    ) -> list[dict[str, Any]]:
        phase_sections = build_template_phase_sections()
        rendered_sections: list[dict[str, Any]] = []
        for phase in phase_sections:
            rendered_rows = []
            for row_code, row_label in phase["rows"]:
                allocation = row_allocations[row_code]
                original_amount = float(allocation["original_budgeted_amount"])
                billed_amount = float(allocation["amount_billed_to_date"])
                remaining_amount = float(allocation["original_budget_amount_remaining"])
                new_amount = float(allocation["new_budgeted_amount"])
                exception_refs = row_exception_refs.get(row_code, [])
                row: dict[str, Any] = {
                    "row_code": row_code,
                    "row_label": row_label,
                    "original_budgeted_amount": original_amount,
                    "amount_billed_to_date": billed_amount,
                    "original_budget_amount_remaining": remaining_amount,
                    "new_budgeted_amount": new_amount,
                    "driver_refs": list(allocation["driver_refs"]),
                    "exception_refs": exception_refs,
                }
                if original_amount == 0.0 and billed_amount == 0.0 and new_amount == 0.0:
                    row["row_note"] = ZERO_ROW_NOTE
                elif exception_refs:
                    row["row_note"] = (
                        "Synthetic draft row flagged for review: "
                        + ", ".join(exception_refs)
                    )
                rendered_rows.append(row)

            rendered_sections.append(
                {
                    "phase_code": phase["phase_code"],
                    "phase_label": phase["phase_label"],
                    "rows": rendered_rows,
                }
            )
        return rendered_sections

    @staticmethod
    def _compute_totals(phase_sections: list[dict[str, Any]]) -> dict[str, float]:
        original_total = 0.0
        billed_total = 0.0
        remaining_total = 0.0
        new_total = 0.0
        for phase in phase_sections:
            for row in phase["rows"]:
                original_total += float(row["original_budgeted_amount"])
                billed_total += float(row["amount_billed_to_date"])
                remaining_total += float(row["original_budget_amount_remaining"])
                new_total += float(row["new_budgeted_amount"])
        return {
            "original_total_budgeted_amount": round(original_total, 2),
            "amount_billed_to_date_total": round(billed_total, 2),
            "original_budget_amount_remaining_total": round(remaining_total, 2),
            "new_total_budgeted_amount": round(new_total, 2),
        }

    @staticmethod
    def _build_row_exception_refs(
        detected_exceptions: list[dict[str, Any]]
    ) -> dict[str, list[str]]:
        refs: dict[str, list[str]] = {}
        for exception in detected_exceptions:
            trigger = exception["trigger"]
            for row_code in ROW_TRIGGER_MAP.get(trigger, []):
                refs.setdefault(row_code, []).append(trigger)
        return refs

    @staticmethod
    def _build_matter_header(case: dict[str, Any]) -> dict[str, Any]:
        matter_profile = case.get("matter_profile", {})
        governance = case.get("governance", {})
        return {
            "matter_family": "synthetic_auto_bi_defense_v1",
            "matter_label_placeholder": matter_profile["matter_label_placeholder"],
            "client_name": {
                "label": "Client Name",
                "value": matter_profile["client_name_placeholder"],
            },
            "client_matter_number": {
                "label": "Client/Matter Number",
                "value": matter_profile["client_matter_number_placeholder"],
            },
            "matter_name": {
                "label": "Matter Name",
                "value": matter_profile["matter_name_placeholder"],
            },
            "claim_number": {
                "label": "Claim Number",
                "value": matter_profile["claim_number_placeholder"],
            },
            "venue_placeholder": matter_profile["venue_placeholder"],
            "litigation_phase": matter_profile["litigation_phase"],
            "carrier_guideline_placeholder_constraint": matter_profile[
                "carrier_guideline_placeholder_constraint"
            ],
            "allowed_use_basis": governance["allowed_use_basis"],
            "sensitivity_level": governance["sensitivity_level"],
            "review_owner": governance["review_owner"],
            "non_production": True,
        }

    @staticmethod
    def _budget_draft_id(case_id: str) -> str:
        case_number = int(str(case_id).split("_")[1])
        return f"BWD-{case_number:06d}"

    @staticmethod
    def _review_path(detected_exceptions: list[dict[str, Any]]) -> str:
        if not detected_exceptions:
            return "none"
        for exception in detected_exceptions:
            mapped = REVIEW_PATH_BY_TRIGGER.get(exception["trigger"])
            if mapped:
                return mapped
        return "review_required"

    @staticmethod
    def _round_amount(amount: float) -> float:
        if amount <= 0:
            return 0.0
        return round(round(amount / 50.0) * 50.0, 2)

    @staticmethod
    def _resolve_schema_path(contract_repo_root: Path) -> Path:
        registry_path = contract_repo_root / "registry" / "schema-registry.json"
        registry = json.loads(registry_path.read_text(encoding="utf-8"))
        for entry in registry.get("schemas", []):
            if entry.get("schema_id") == VIEW_BUDGET_SCHEMA_ID:
                relative_path = entry.get("path")
                if isinstance(relative_path, str):
                    schema_path = contract_repo_root / relative_path
                    if schema_path.exists():
                        return schema_path
                break
        raise ValueError(f"Unable to resolve {VIEW_BUDGET_SCHEMA_ID} from schema-registry.json.")
