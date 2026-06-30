from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from scripts.validate_intake_lake_admission_review import (
    IntakeLakeAdmissionReviewError,
    validate_intake_lake_admission_review,
)


ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "registry" / "intake-lake-admission-review-registry.json"
VALIDATOR = ROOT / "scripts" / "validate_intake_lake_admission_review.py"


def _registry_payload() -> dict:
    return json.loads(REGISTRY.read_text(encoding="utf-8"))


def test_intake_lake_admission_review_registry_validates() -> None:
    data = validate_intake_lake_admission_review()

    assert data["status"] == "candidate_review_only"
    assert data["non_authoritative"] is True
    assert data["sqlite_migrations_authorized"] is False
    assert data["raw_legal_payload_storage_authorized"] is False


def test_intake_lake_admission_review_validator_cli_passes() -> None:
    completed = subprocess.run(
        [sys.executable, str(VALIDATOR)],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )

    assert completed.returncode == 0, completed.stderr
    assert "validation passed" in completed.stdout


def test_review_items_do_not_assign_canon_or_storage_authority() -> None:
    data = _registry_payload()

    for item in data["review_items"]:
        policy = item["event_mapping_policy"]
        controls = item["required_admission_controls"]
        assert item["label_authority"] == "local_operational_label_only"
        assert item["local_admission_label"].startswith("exception_lake.local.")
        assert policy["canonical_route_id_assignment"] == "none"
        assert policy["canonical_event_class_assignment"] == "none"
        assert controls["append_only"] is True
        assert controls["raw_payload_storage_allowed"] is False
        assert controls["sqlite_migration_authorized_now"] is False
        assert controls["real_data_authorized_now"] is False
        assert "sqlite_migration" in item["prohibited_actions"]
        assert "raw_legal_payload_storage" in item["prohibited_actions"]


def test_budget_review_keeps_actuals_comparison_fields() -> None:
    data = _registry_payload()
    budget = next(
        item
        for item in data["review_items"]
        if item["source_proposal_id"] == "lake.intake-budget-evidence-mapping.v0_1"
    )

    assert "budget_actual_comparison" in budget["candidate_record_families"]
    assert "proposed_budget_amount" in budget["budget_actuals_comparison_fields"]
    assert (
        "carrier_compliant_projection_amount"
        in budget["budget_actuals_comparison_fields"]
    )
    assert (
        "approved_budget_amount_if_known" in budget["budget_actuals_comparison_fields"]
    )
    assert "actual_billed_amount" in budget["budget_actuals_comparison_fields"]
    assert (
        "write_down_or_disallowed_amount" in budget["budget_actuals_comparison_fields"]
    )


def test_carrier_review_captures_unknown_bucket_appeals_and_financial_outcomes() -> (
    None
):
    data = _registry_payload()
    carrier = next(
        item
        for item in data["review_items"]
        if item["source_proposal_id"] == "lake.carrier-rejection-admission.v0_1"
    )

    assert {entry["source"] for entry in carrier["future_capture_sources"]} == {
        "email",
        "carrier_portal",
    }
    assert all(
        entry["enabled_now"] is False for entry in carrier["future_capture_sources"]
    )
    assert "unknown_or_new_rejection_pattern" in carrier["candidate_rejection_buckets"]
    assert "carrier_appeal_result" in carrier["candidate_record_families"]
    assert "closed_financial_outcome_recorded" in carrier["required_state_chain"]
    assert "new_rejection_pattern_candidate" in carrier["learning_loop_inputs"]


def test_validator_rejects_missing_unknown_rejection_bucket(tmp_path: Path) -> None:
    data = _registry_payload()
    carrier = next(
        item
        for item in data["review_items"]
        if item["source_proposal_id"] == "lake.carrier-rejection-admission.v0_1"
    )
    carrier["candidate_rejection_buckets"].remove("unknown_or_new_rejection_pattern")
    bad_registry = tmp_path / "bad_registry.json"
    bad_registry.write_text(json.dumps(data), encoding="utf-8")

    with pytest.raises(
        IntakeLakeAdmissionReviewError,
        match="unknown_or_new_rejection_pattern",
    ):
        validate_intake_lake_admission_review(bad_registry)
