from __future__ import annotations

import json
from pathlib import Path

import pytest

from exceptions_lake_runtime.budget_template_rows import ordered_phase_codes, ordered_row_codes
from exceptions_lake_runtime.event_store import EventStore
from exceptions_lake_runtime.insurance_budget_poc import (
    classify_case,
    detect_budget_exceptions,
    run_case,
)


CASE_FILES = (
    "case_01_baseline_compliant.synthetic.json",
    "case_02_guideline_lookup_miss.synthetic.json",
    "case_03_missing_budget_driver.synthetic.json",
    "case_04_expert_gap.synthetic.json",
    "case_05_deposition_and_trial_drift.synthetic.json",
    "case_06_appeal_and_staffing_conflict.synthetic.json",
    "case_07_unsupported_assumption_or_missing_provenance.synthetic.json",
    "case_08_missing_allowed_use_and_owner.synthetic.json",
)

EVENT_PATH_CASES = CASE_FILES[:6]
PREFLIGHT_CASES = CASE_FILES[6:]


def _load_case(runtime_repo_root: Path, case_name: str) -> dict:
    case_path = runtime_repo_root / "examples" / "insurance_budget_poc" / case_name
    return json.loads(case_path.read_text(encoding="utf-8"))


def _snapshot_repo_contents(root: Path) -> dict[str, str]:
    import hashlib

    snapshot: dict[str, str] = {}
    for file_path in sorted(root.rglob("*")):
        if not file_path.is_file():
            continue
        if ".git" in file_path.parts:
            continue
        digest = hashlib.sha256(file_path.read_bytes()).hexdigest()
        snapshot[str(file_path.relative_to(root))] = digest
    return snapshot


@pytest.mark.parametrize("case_name", CASE_FILES)
def test_classify_case_matches_expected_synthetic_classifications(
    runtime_repo_root: Path, case_name: str
) -> None:
    case = _load_case(runtime_repo_root, case_name)
    actual = classify_case(case)

    for key, value in case["runtime_expectations"]["expected_classifications"].items():
        assert actual[key] == value


@pytest.mark.parametrize("case_name", CASE_FILES)
def test_detect_budget_exceptions_matches_expected_triggers(
    runtime_repo_root: Path, case_name: str
) -> None:
    case = _load_case(runtime_repo_root, case_name)

    detected = detect_budget_exceptions(case, classify_case(case))

    assert [item["trigger"] for item in detected] == case["runtime_expectations"][
        "expected_exception_triggers"
    ]


@pytest.mark.parametrize("case_name", EVENT_PATH_CASES)
def test_run_case_event_path_generates_template_shaped_budget_and_expected_events(
    runtime_repo_root: Path, runtime_config, case_name: str
) -> None:
    case = _load_case(runtime_repo_root, case_name)
    before_snapshot = _snapshot_repo_contents(runtime_config.contract_repo_root)

    result = run_case(case, config=runtime_config)

    after_snapshot = _snapshot_repo_contents(runtime_config.contract_repo_root)
    event_store = EventStore(runtime_config.event_store_path)
    stored_records = event_store.list_records()
    expected_triggers = case["runtime_expectations"]["expected_exception_triggers"]
    budget_draft = result["budget_draft"]

    assert result["case_id"] == case["case_id"]
    assert result["non_production"] is True
    assert [item["trigger"] for item in result["detected_exceptions"]] == expected_triggers
    assert result["preflight_result"] is None
    assert before_snapshot == after_snapshot
    assert (budget_draft is not None) is case["runtime_expectations"]["expected_budget_draft_present"]
    assert result["review_packet"] is not None
    assert result["review_packet"]["review_path"] == case["runtime_expectations"]["expected_review_path"]
    assert budget_draft["candidate_status"] == "synthetic_candidate_not_canonical"
    assert budget_draft["non_claims"][0] == "synthetic placeholder amounts only"
    assert [section["phase_code"] for section in budget_draft["phase_sections"]] == ordered_phase_codes()
    assert [
        row["row_code"]
        for section in budget_draft["phase_sections"]
        for row in section["rows"]
    ] == ordered_row_codes()
    assert budget_draft["summary"]["original_budget_value"] == budget_draft["totals"]["original_total_budgeted_amount"]
    assert budget_draft["summary"]["updated_budget_value"] == budget_draft["totals"]["new_total_budgeted_amount"]

    computed_original = round(
        sum(
            row["original_budgeted_amount"]
            for section in budget_draft["phase_sections"]
            for row in section["rows"]
        ),
        2,
    )
    computed_billed = round(
        sum(
            row["amount_billed_to_date"]
            for section in budget_draft["phase_sections"]
            for row in section["rows"]
        ),
        2,
    )
    computed_remaining = round(
        sum(
            row["original_budget_amount_remaining"]
            for section in budget_draft["phase_sections"]
            for row in section["rows"]
        ),
        2,
    )
    computed_new = round(
        sum(
            row["new_budgeted_amount"]
            for section in budget_draft["phase_sections"]
            for row in section["rows"]
        ),
        2,
    )
    assert computed_original == budget_draft["totals"]["original_total_budgeted_amount"]
    assert computed_billed == budget_draft["totals"]["amount_billed_to_date_total"]
    assert computed_remaining == budget_draft["totals"]["original_budget_amount_remaining_total"]
    assert computed_new == budget_draft["totals"]["new_total_budgeted_amount"]

    if not expected_triggers:
        assert result["ingested_events"] == []
        assert result["pressure_candidate"] is None
        assert stored_records == []
        assert result["review_packet"]["status"] == "no_exception_candidate_generated"
        return

    assert len(result["ingested_events"]) == len(expected_triggers)
    assert all(item["accepted"] is True for item in result["ingested_events"])
    assert all(item["stored"] is True for item in result["ingested_events"])
    assert all(record["validation_result"]["valid"] is True for record in stored_records)
    assert result["pressure_candidate"]["candidate_status"] == "synthetic_candidate_not_canonical"
    assert (
        result["pressure_candidate"]["pressure_vector"]["vector_class"]
        == case["runtime_expectations"]["expected_pressure_vector_class"]
    )
    assert result["review_packet"]["status"] == "review_required"


@pytest.mark.parametrize("case_name", PREFLIGHT_CASES)
def test_run_case_preflight_blockers_fail_closed_without_event_persistence(
    runtime_repo_root: Path, runtime_config, case_name: str
) -> None:
    case = _load_case(runtime_repo_root, case_name)
    before_snapshot = _snapshot_repo_contents(runtime_config.contract_repo_root)

    result = run_case(case, config=runtime_config)

    after_snapshot = _snapshot_repo_contents(runtime_config.contract_repo_root)
    event_store = EventStore(runtime_config.event_store_path)

    assert result["case_id"] == case["case_id"]
    assert result["non_production"] is True
    assert result["budget_draft"] is None
    assert result["ingested_events"] == []
    assert result["pressure_candidate"] is None
    assert result["preflight_result"] is not None
    assert result["preflight_result"]["mode"] == "non_synthetic_dry_run_preflight"
    assert result["preflight_result"]["preflight_ready"] is False
    assert [item["trigger"] for item in result["detected_exceptions"]] == case[
        "runtime_expectations"
    ]["expected_exception_triggers"]
    assert event_store.list_records() == []
    assert before_snapshot == after_snapshot
    assert result["review_packet"]["status"] == "preflight_blocked"
    assert result["review_packet"]["review_path"] == case["runtime_expectations"]["expected_review_path"]

    for field_name in case["runtime_expectations"]["expected_preflight_missing"]:
        assert field_name in result["preflight_result"]["readiness_result"]["missing"]
