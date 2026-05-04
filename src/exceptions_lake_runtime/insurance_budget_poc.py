from __future__ import annotations

import copy
from typing import Any

from .audit_log import AuditLog
from .api import build_non_synthetic_preflight_envelope, build_synthetic_envelope
from .budget_draft_generator import BudgetDraftGenerator
from .config import RuntimeConfig
from .contract_loader import ContractLoader
from .event_ingestion import EventIngestionService
from .event_store import EventStore
from .non_synthetic_readiness import NonSyntheticReadinessChecker
from .policy_gateway import PolicyGateway
from .pressure_builder import PressureBuilder
from .validation_gateway import ValidationGateway


EVENT_CONFIG = {
    "synthetic_guideline_lookup_miss": {
        "event_class": "retrieval_miss",
        "route_id": "route.retrieval_miss.v1",
        "destination_loop": "retrieval_tuning",
        "origin_layer": "retrieval",
        "pressure_class": "retrieval_quality_pressure",
        "severity": "moderate",
        "review_path": "knowledge_owner_review_and_retrieval_tuning_opportunity_candidate",
    },
    "missing_required_budget_driver": {
        "event_class": "workflow_escalation",
        "route_id": "route.workflow_escalation.v1",
        "destination_loop": "workflow_redesign",
        "origin_layer": "workflow",
        "pressure_class": "workflow_friction_pressure",
        "severity": "moderate",
        "review_path": "budget_ops_review_and_workflow_redesign_candidate",
    },
    "budget_phase_missing": {
        "event_class": "workflow_escalation",
        "route_id": "route.workflow_escalation.v1",
        "destination_loop": "workflow_redesign",
        "origin_layer": "workflow",
        "pressure_class": "workflow_friction_pressure",
        "severity": "high",
        "review_path": "budget_ops_and_billing_integrity_review",
    },
    "budget_exceeds_synthetic_threshold": {
        "event_class": "workflow_escalation",
        "route_id": "route.workflow_escalation.v1",
        "destination_loop": "workflow_redesign",
        "origin_layer": "workflow",
        "pressure_class": "workflow_friction_pressure",
        "severity": "high",
        "review_path": "billing_integrity_review",
    },
    "staffing_mix_outside_expected_pattern": {
        "event_class": "workflow_escalation",
        "route_id": "route.workflow_escalation.v1",
        "destination_loop": "workflow_redesign",
        "origin_layer": "workflow",
        "pressure_class": "workflow_friction_pressure",
        "severity": "high",
        "review_path": "billing_integrity_review",
    },
    "expert_need_not_reflected_in_L130_L340_E119": {
        "event_class": "workflow_escalation",
        "route_id": "route.workflow_escalation.v1",
        "destination_loop": "workflow_redesign",
        "origin_layer": "workflow",
        "pressure_class": "workflow_friction_pressure",
        "severity": "high",
        "review_path": "billing_integrity_review",
    },
    "deposition_burden_not_reflected_in_L330_E115": {
        "event_class": "workflow_escalation",
        "route_id": "route.workflow_escalation.v1",
        "destination_loop": "workflow_redesign",
        "origin_layer": "workflow",
        "pressure_class": "workflow_friction_pressure",
        "severity": "high",
        "review_path": "billing_integrity_and_workflow_review",
    },
    "trial_likelihood_not_reflected_in_L400": {
        "event_class": "workflow_escalation",
        "route_id": "route.workflow_escalation.v1",
        "destination_loop": "workflow_redesign",
        "origin_layer": "workflow",
        "pressure_class": "workflow_friction_pressure",
        "severity": "high",
        "review_path": "billing_integrity_and_workflow_review",
    },
    "appeal_likelihood_not_reflected_in_L500": {
        "event_class": "workflow_escalation",
        "route_id": "route.workflow_escalation.v1",
        "destination_loop": "workflow_redesign",
        "origin_layer": "workflow",
        "pressure_class": "workflow_friction_pressure",
        "severity": "high",
        "review_path": "billing_integrity_review",
    },
    "amount_billed_to_date_incompatible_with_remaining_budget": {
        "event_class": "workflow_escalation",
        "route_id": "route.workflow_escalation.v1",
        "destination_loop": "workflow_redesign",
        "origin_layer": "workflow",
        "pressure_class": "workflow_friction_pressure",
        "severity": "high",
        "review_path": "billing_integrity_and_workflow_review",
    },
}
TRIGGER_ORDER = (
    "synthetic_guideline_lookup_miss",
    "missing_required_budget_driver",
    "budget_phase_missing",
    "budget_exceeds_synthetic_threshold",
    "staffing_mix_outside_expected_pattern",
    "expert_need_not_reflected_in_L130_L340_E119",
    "deposition_burden_not_reflected_in_L330_E115",
    "trial_likelihood_not_reflected_in_L400",
    "appeal_likelihood_not_reflected_in_L500",
    "amount_billed_to_date_incompatible_with_remaining_budget",
    "unsupported_budget_assumption",
    "allowed_use_basis_missing",
    "source_provenance_missing",
)
NON_CLAIMS = [
    "synthetic test-only budget draft",
    "no production budget accuracy claimed",
    "no real client data or real matters",
    "no canonical mutation",
]


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


def classify_case(case: dict[str, Any]) -> dict[str, Any]:
    matter_profile = case.get("matter_profile", {})
    budget_profile = case.get("budget_profile", {})
    governance = case.get("governance", {})
    readiness_request = case.get("readiness_request", {})
    row_emphasis = _derive_row_emphasis(matter_profile)
    allowed_use_basis = governance.get("allowed_use_basis")
    provenance_available = readiness_request.get("evidence_provenance_available", True)

    if (
        case.get("flow_mode") == "non_synthetic_dry_run_preflight"
        or not allowed_use_basis
        or provenance_available is not True
        or budget_profile.get("supported_budget_assumptions") is False
    ):
        risk_class = "governance_blocker"
    elif (
        matter_profile.get("trial_likelihood") == "high"
        or matter_profile.get("appeal_likelihood") in {"medium", "high"}
        or matter_profile.get("expert_need") == "required"
        or budget_profile.get("synthetic_gap_refs")
    ):
        risk_class = "budget_integrity_high"
    elif budget_profile.get("guideline_lookup_status") == "miss" or matter_profile.get(
        "liability_clarity"
    ) in {"mixed", "disputed"}:
        risk_class = "budget_integrity_medium"
    else:
        risk_class = "budget_integrity_low"

    return {
        "matter_type": matter_profile.get("matter_type"),
        "venue_placeholder": matter_profile.get("venue_placeholder"),
        "litigation_phase": matter_profile.get("litigation_phase"),
        "injury_severity_band": matter_profile.get("injury_severity_band"),
        "liability_clarity": matter_profile.get("liability_clarity"),
        "medical_specials_band": matter_profile.get("medical_specials_band"),
        "claimant_attorney_involvement": matter_profile.get(
            "claimant_attorney_involvement"
        ),
        "uninsured_or_coverage_complication_indicator": matter_profile.get(
            "uninsured_or_coverage_complication_indicator"
        ),
        "seatbelt_restraint_factor": matter_profile.get("seatbelt_restraint_factor"),
        "fact_witness_count_band": matter_profile.get("fact_witness_count_band"),
        "expert_need": matter_profile.get("expert_need"),
        "written_discovery_burden": matter_profile.get("written_discovery_burden"),
        "deposition_burden": matter_profile.get("deposition_burden"),
        "dispositive_motion_likelihood": matter_profile.get(
            "dispositive_motion_likelihood"
        ),
        "mediation_likelihood": matter_profile.get("mediation_likelihood"),
        "trial_likelihood": matter_profile.get("trial_likelihood"),
        "appeal_likelihood": matter_profile.get("appeal_likelihood"),
        "budget_phase": budget_profile.get("budget_phase"),
        "staffing_assumption": budget_profile.get("staffing_assumption"),
        "budget_variance_signal": budget_profile.get("budget_variance_signal"),
        "carrier_guideline_placeholder_constraint": matter_profile.get(
            "carrier_guideline_placeholder_constraint"
        ),
        "row_emphasis": row_emphasis,
        "review_owner": governance.get("review_owner"),
        "allowed_use_basis": allowed_use_basis,
        "sensitivity_level": governance.get("sensitivity_level"),
        "risk_class": risk_class,
        "canon_influence_boundary": governance.get("canon_influence_boundary"),
    }


def detect_budget_exceptions(
    case: dict[str, Any], classifications: dict[str, Any]
) -> list[dict[str, Any]]:
    matter_profile = case.get("matter_profile", {})
    budget_profile = case.get("budget_profile", {})
    governance = case.get("governance", {})
    readiness_request = case.get("readiness_request", {})

    required_budget_drivers = list(budget_profile.get("required_budget_drivers", []))
    provided_budget_drivers = set(budget_profile.get("provided_budget_drivers", []))
    missing_budget_drivers = [
        driver for driver in required_budget_drivers if driver not in provided_budget_drivers
    ]

    triggers: list[str] = []
    if budget_profile.get("guideline_lookup_status") == "miss":
        triggers.append("synthetic_guideline_lookup_miss")
    if missing_budget_drivers:
        triggers.append("missing_required_budget_driver")
    if budget_profile.get("phase_budget_present") is False:
        triggers.append("budget_phase_missing")
    if budget_profile.get("exceeds_synthetic_threshold") is True:
        triggers.append("budget_exceeds_synthetic_threshold")
    if budget_profile.get("staffing_pattern_expected") and (
        budget_profile.get("staffing_pattern_actual")
        != budget_profile.get("staffing_pattern_expected")
    ):
        triggers.append("staffing_mix_outside_expected_pattern")
    gap_refs = set(budget_profile.get("synthetic_gap_refs", []))
    if "L130" in gap_refs or "L340" in gap_refs or "E119" in gap_refs:
        triggers.append("expert_need_not_reflected_in_L130_L340_E119")
    if "L330" in gap_refs or "E115" in gap_refs:
        triggers.append("deposition_burden_not_reflected_in_L330_E115")
    if "L400" in gap_refs:
        triggers.append("trial_likelihood_not_reflected_in_L400")
    if "L500" in gap_refs:
        triggers.append("appeal_likelihood_not_reflected_in_L500")
    if budget_profile.get("billed_remaining_incompatible") is True:
        triggers.append("amount_billed_to_date_incompatible_with_remaining_budget")
    if budget_profile.get("supported_budget_assumptions") is False:
        triggers.append("unsupported_budget_assumption")
    if not governance.get("allowed_use_basis"):
        triggers.append("allowed_use_basis_missing")
    if readiness_request.get("evidence_provenance_available", True) is not True:
        triggers.append("source_provenance_missing")

    exceptions: list[dict[str, Any]] = []
    for trigger in TRIGGER_ORDER:
        if trigger not in triggers:
            continue
        config = EVENT_CONFIG.get(trigger)
        if config is None:
            exceptions.append(
                {
                    "trigger": trigger,
                    "event_class": None,
                    "route_id": None,
                    "destination_loop": None,
                    "origin_layer": "governance",
                    "pressure_class": None,
                    "review_path": (
                        "dry_run_preflight_rejection_and_governance_remediation"
                        if trigger == "source_provenance_missing"
                        else "dry_run_preflight_rejection"
                    ),
                    "severity": "high",
                    "summary": (
                        f"Synthetic {trigger.replace('_', ' ')} detected for "
                        f"{case.get('case_id')}."
                    ),
                    "details": (
                        "Synthetic governance blocker only. This trigger must fail "
                        "closed through the dry-run preflight path and may not "
                        "persist a runtime event."
                    ),
                    "missing_budget_drivers": missing_budget_drivers,
                }
            )
            continue
        exceptions.append(
            {
                "trigger": trigger,
                "event_class": config["event_class"],
                "route_id": config["route_id"],
                "destination_loop": config["destination_loop"],
                "origin_layer": config["origin_layer"],
                "pressure_class": config["pressure_class"],
                "review_path": config["review_path"],
                "severity": config["severity"],
                "summary": (
                    f"Synthetic {trigger.replace('_', ' ')} detected for "
                    f"{case.get('case_id')} in {matter_profile.get('matter_type')}."
                ),
                "details": (
                    "Synthetic insurance-defense budget learning signal only. "
                    f"Expected review path: {config['review_path']}."
                ),
                "missing_budget_drivers": missing_budget_drivers,
            }
        )
    return exceptions


def map_exception_to_envelope(case: dict[str, Any], exception: dict[str, Any]) -> dict[str, Any]:
    sequence = int(exception.get("sequence", 1))
    case_id = str(case.get("case_id", "case_00_unknown"))
    case_number = int(case_id.split("_")[1])
    exception_id = f"EXC-9{case_number:02d}{sequence:03d}"
    governance = case.get("governance", {})

    return {
        "exception_id": exception_id,
        "schema_type": "exception-event",
        "schema_version": "v1",
        "event_class": exception["event_class"],
        "severity": exception["severity"],
        "event_time": case.get("synthetic_time", "2026-04-26T00:00:00Z"),
        "summary": exception["summary"],
        "details": exception["details"],
        "origin": {
            "layer": exception["origin_layer"],
            "component": "synthetic-insurance-budget-poc",
            "run_id": f"{case_id}-run",
            "artifact_refs": [f"synthetic:{case_id}"],
            "policy_refs": ["synthetic-budget-learning-poc"],
        },
        "route": {
            "route_id": exception["route_id"],
            "destination_loop": exception["destination_loop"],
            "promotion_gate_required": True,
        },
        "trust_metadata": {
            "authority_zone": "synthetic-lab",
            "trust_level": "high" if exception["severity"] in {"high", "critical"} else "moderate",
            "confidence": 0.88 if exception["event_class"] == "retrieval_miss" else 0.84,
            "reviewer_required": True,
            "review_role": governance.get("review_owner") or "synthetic_governance_owner",
        },
        "canonical_mutation_control": {
            "direct_mutation_attempted": False,
            "allowed_action": "route_for_review",
            "boundary_note": "promotion_decision_required_for_canonical_change",
        },
    }


def run_case(case: dict[str, Any], config: RuntimeConfig | None = None) -> dict[str, Any]:
    services = _build_runtime_services(config=config)
    classifications = classify_case(copy.deepcopy(case))
    detected_exceptions = detect_budget_exceptions(copy.deepcopy(case), classifications)
    budget_generator = BudgetDraftGenerator(services["contract_bundle"])

    result = {
        "case_id": case.get("case_id"),
        "classifications": classifications,
        "budget_draft": None,
        "detected_exceptions": detected_exceptions,
        "ingested_events": [],
        "pressure_candidate": None,
        "preflight_result": None,
        "review_packet": None,
        "non_production": True,
    }

    if case.get("flow_mode") == "non_synthetic_dry_run_preflight":
        readiness_request = copy.deepcopy(case.get("readiness_request", {}))
        readiness_request["contract_sha"] = (
            services["contract_bundle"].locked_contract_sha
            or services["contract_bundle"].contract_version
        )
        preflight_envelope = build_non_synthetic_preflight_envelope(
            readiness_request, actor="synthetic-test-runner"
        )
        result["preflight_result"] = services["ingestion_service"].ingest(
            preflight_envelope
        )
        result["review_packet"] = _build_review_packet(
            case=case,
            classifications=classifications,
            detected_exceptions=detected_exceptions,
            ingested_events=[],
            pressure_candidate=None,
            preflight_result=result["preflight_result"],
            budget_draft_id=None,
        )
        return result

    for index, exception in enumerate(detected_exceptions, start=1):
        if exception["trigger"] not in EVENT_CONFIG:
            raise ValueError(
                f"Unsupported governance-blocker trigger on synthetic event path: {exception['trigger']}"
            )
        payload = map_exception_to_envelope(
            case, {**exception, "sequence": index}
        )
        envelope = build_synthetic_envelope(payload, actor="synthetic-test-runner")
        result["ingested_events"].append(services["ingestion_service"].ingest(envelope))

    if any(event.get("accepted") for event in result["ingested_events"]):
        result["pressure_candidate"] = PressureBuilder(
            services["contract_bundle"], event_store=services["event_store"]
        ).build_candidate()

    ingested_event_ids = [
        event["event_id"] for event in result["ingested_events"] if event.get("accepted") is True
    ]
    pressure_status = (
        result["pressure_candidate"]["candidate_status"]
        if result["pressure_candidate"] is not None
        else None
    )
    result["budget_draft"] = budget_generator.generate(
        case,
        classifications,
        detected_exceptions,
        ingested_event_ids=ingested_event_ids,
        pressure_candidate_status=pressure_status,
    )
    result["review_packet"] = _build_review_packet(
        case=case,
        classifications=classifications,
        detected_exceptions=detected_exceptions,
        ingested_events=result["ingested_events"],
        pressure_candidate=result["pressure_candidate"],
        preflight_result=None,
        budget_draft_id=result["budget_draft"]["budget_draft_id"],
    )

    return result


def _derive_row_emphasis(matter_profile: dict[str, Any]) -> list[str]:
    emphasis = ["L110", "L120", "L150"]
    if matter_profile.get("litigation_phase") in {
        "written_discovery",
        "depositions",
        "expert",
        "mediation",
        "trial_prep",
    }:
        emphasis.append("L310")
    if matter_profile.get("written_discovery_burden") in {"moderate", "heavy"}:
        emphasis.append("L320")
    if matter_profile.get("deposition_burden") in {"limited", "heavy"}:
        emphasis.extend(["L330", "E115"])
    if matter_profile.get("expert_need") in {"possible", "required"}:
        emphasis.extend(["L130", "L340", "E119"])
    if matter_profile.get("trial_likelihood") in {"medium", "high"}:
        emphasis.append("L400")
    if matter_profile.get("appeal_likelihood") in {"medium", "high"}:
        emphasis.append("L500")
    if matter_profile.get("mediation_likelihood") in {"medium", "high"}:
        emphasis.append("L160")
    if matter_profile.get("dispositive_motion_likelihood") in {"medium", "high"}:
        emphasis.append("L240")
    return list(dict.fromkeys(emphasis))


def _build_review_packet(
    *,
    case: dict[str, Any],
    classifications: dict[str, Any],
    detected_exceptions: list[dict[str, Any]],
    ingested_events: list[dict[str, Any]],
    pressure_candidate: dict[str, Any] | None,
    preflight_result: dict[str, Any] | None,
    budget_draft_id: str | None,
) -> dict[str, Any]:
    accepted_event_ids = [
        item["event_id"] for item in ingested_events if item.get("accepted") is True
    ]
    if preflight_result is not None:
        status = "preflight_blocked"
        review_path = "dry_run_preflight_rejection"
    elif detected_exceptions:
        status = "review_required"
        review_path = detected_exceptions[0]["review_path"]
    else:
        status = "no_exception_candidate_generated"
        review_path = "none"

    return {
        "case_id": case["case_id"],
        "status": status,
        "review_owner": classifications.get("review_owner") or "synthetic_governance_owner",
        "review_path": review_path,
        "budget_draft_id": budget_draft_id,
        "detected_exception_triggers": [item["trigger"] for item in detected_exceptions],
        "ingested_event_ids": accepted_event_ids,
        "pressure_candidate_status": (
            pressure_candidate["candidate_status"] if pressure_candidate else None
        ),
        "preflight_required": preflight_result is not None,
        "refusal_behavior": (
            "fail_closed_without_final_budget_draft"
            if preflight_result is not None
            else "review_packet_for_non_canonical_budget_draft"
        ),
        "non_claims": list(NON_CLAIMS),
    }
