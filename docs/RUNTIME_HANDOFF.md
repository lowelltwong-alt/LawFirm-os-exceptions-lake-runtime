# Runtime Handoff

## What is implemented

This runtime repo currently implements:

- contract loading from the Law Firm OS Semantic Substrate contract repository (local path via `EXCEPTIONS_LAKE_CONTRACT_REPO_PATH`)
- contract version pinning through `contracts.lock.json`
- synthetic `exception-event` validation
- deny-by-default runtime policy enforcement
- append-only local event storage
- append-only local audit logging
- non-canonical pressure-vector candidate generation
- dry-run-only non-synthetic readiness preflight

## What is safe to run

- `python -m pip install -e ".[dev]"`
- `pytest`
- `python scripts/update_contract_lock.py`
- `exceptions-lake health`
- `exceptions-lake ingest-synthetic examples/synthetic_exception_event.json`
- `exceptions-lake list-events`
- `exceptions-lake build-pressure-candidate`
- `exceptions-lake non-synthetic-preflight examples/non_synthetic_readiness.example.json`
- `exceptions-lake refresh-contract-lock`
- local synthetic ingestion flows
- metadata-only `non_synthetic_dry_run_preflight`

## Contract repo setup

Set the contract repo path before local validation:

```powershell
$env:EXCEPTIONS_LAKE_CONTRACT_REPO_PATH = 'C:\path\to\LawFirm-os-semantic-substrate'
```

Refresh the lock file when intentionally moving to a new reviewed contract SHA:

```powershell
python scripts/update_contract_lock.py
```

## What is forbidden

- real firm operational data ingestion
- live connectors
- dashboards
- deployment secrets or production configuration
- canon mutation
- writing into the contract repo

## Before first real data

The following must happen in a later PR before any real data admission is considered:

- connector scope approval
- source-ingestion manifest and provenance coverage
- sensitivity and allowed-use review
- business, access, and validation ownership signoff
- rollback or quarantine plan review
- dry-run preflight approval
- explicit policy and runtime boundary review

## Recommended first pilot candidates

When the project is ready for a later connector-scoping PR, the safest first pilot candidates are still metadata-bounded and low-volume:

- a governed dry run over one approved source-ingestion manifest family
- a retrieval-miss review slice using exported synthetic or scrubbed metadata only
- a workflow exception candidate feed that remains non-canonical and review-gated

Those are future pilot candidates only. They are not enabled by this PR.
