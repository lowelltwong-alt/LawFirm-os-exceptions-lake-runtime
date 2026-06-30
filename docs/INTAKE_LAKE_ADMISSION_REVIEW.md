# Intake Lake Admission Review

## Purpose

This is an Exception Lake owner review docket for the intake-to-budget vertical proposals emitted by `LawFirm-os-intake`.

The docket is candidate-only. It does not create canonical route IDs, event classes, schemas, SQLite tables, migrations, connector authority, raw-payload storage authority, real-data pilot authority, budget submission authority, appeal submission authority, or promotion authority.

The local registry is `registry/intake-lake-admission-review-registry.json`.

## Orchestrator Review Packet Validation

`LawFirm-os-orchestrator` may produce an `intake_lake_admission_review_packet.v0_1` artifact after its local intake owner-review packet is built. Exception Lake validates that artifact with:

```powershell
python scripts/validate_intake_lake_admission_review_packet.py --packet path/to/intake_lake_admission_review_packet.json --report-out path/to/validation_report.json
```

The validator recomputes packet and candidate-record hashes, checks source-hash shape, verifies candidate record families against this docket, and rejects any packet that claims Lake write authority, SQLite write authority, raw-payload storage, real-data admission, external writes, canonical route/event assignment, budget submission authority, appeal submission authority, or admitted records.

The optional report is local review evidence only. It is not an Exception Lake admission record and does not append to runtime storage.

## Source Package

Read-only source: `LawFirm-os-intake:promotion/cross_repo_promotion_package.json`.

The current Lake review items are:

- `lake.intake-budget-evidence-mapping.v0_1`
- `lake.carrier-rejection-admission.v0_1`

## Intake And Budget Evidence Mapping

Future Lake adoption should review append-only candidate record families for:

- intake proposal packets;
- human corrections and supersessions;
- intake escalation or blocker records;
- budget template mapping reports;
- human budget change records;
- budget revision deltas;
- budget actual comparisons;
- variance-driver learning candidates.

Each future candidate record should carry source refs, source hashes, an Orchestrator evidence packet hash, a record hash, an idempotency key, and a previous-record hash or explicit null. Corrections append superseding records; they do not mutate the original record.

Budget actuals comparison must keep separate numbers for proposed budget, carrier-compliant projection, approved budget when known, actual billed amount, and disallowed or written-down amount.

## Carrier Rejection Admission

Carrier rejection capture must be deterministic at the envelope level. Every future notice should be capturable as a known candidate bucket or as `unknown_or_new_rejection_pattern`.

That unknown bucket is required because carrier portals and emails will change faster than canonical vocabularies. Unknown patterns should become reviewed learning candidates, not silent schema drift.

Future carrier rejection records should append through a state chain:

```text
received_candidate
-> reconciled_to_budget_or_invoice
-> human_review_required
-> fix_or_appeal_strategy_selected
-> appeal_authorized_by_human
-> appeal_submitted_by_authorized_channel
-> appeal_result_received
-> closed_financial_outcome_recorded
-> learning_candidate_prepared
```

Email and carrier portal capture are disabled now. This docket records metadata requirements only.

## Current Non-Authorization

This slice does not add SQLite migrations, connector code, real data ingestion, raw notice payload storage, canonical event mapping, or default Lake writes. It only makes the evidence-plane owner review deterministic.

## Validation

Run:

```powershell
python scripts/validate_intake_lake_admission_review.py
python scripts/validate_intake_lake_admission_review_packet.py --packet path/to/intake_lake_admission_review_packet.json --report-out path/to/validation_report.json
python scripts/run_full_pytest.py tests/test_intake_lake_admission_review.py -q
python scripts/run_full_pytest.py tests/test_intake_lake_admission_review_packet.py -q
```
