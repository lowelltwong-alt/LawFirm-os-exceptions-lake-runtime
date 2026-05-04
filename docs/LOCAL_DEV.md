# Local Development

## Prerequisites

- Python 3.11+
- a local checkout of your **Law Firm ontology** contract repository (example GitHub slug: `your-org/law-firm-ontology`)

## CI-equivalent command sequence (local-first)

Run these in order from the **runtime repo root** so your machine matches `.github/workflows/ci.yml`:

**PowerShell**

```powershell
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
python scripts/ci_check_contract_lock.py
$env:EXCEPTIONS_LAKE_CONTRACT_REPO_PATH = 'C:\path\to\law-firm-ontology-contracts'
python -m pytest
```

**Bash**

```bash
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
python scripts/ci_check_contract_lock.py
export EXCEPTIONS_LAKE_CONTRACT_REPO_PATH="/path/to/law-firm-ontology-contracts"
python -m pytest
```

Tests copy contract files from your checkout into a temporary git-backed fixture and temporarily repin `contracts.lock.json` to that fixture’s `HEAD` SHA, so your ontology checkout only needs to be a complete tree at a commit that includes the required contract files. CI checks out the public Law Firm ontology contract repository at the `contract_sha` pinned in this repo’s lock file (clone source: `CONTRACT_ONTOLOGY_REPOSITORY` in the workflow file) for reproducible fixtures (no firm data).

## Setup

Set the contract repo path:

```powershell
$env:EXCEPTIONS_LAKE_CONTRACT_REPO_PATH = 'C:\path\to\law-firm-ontology-contracts'
```

Install the runtime repo:

```powershell
python -m pip install -e ".[dev]"
```

Refresh the contract pin when you intentionally adopt a new contract repo SHA:

```powershell
python scripts/update_contract_lock.py
```

See also:

- `docs/RUNTIME_HANDOFF.md`
- `docs/NON_SYNTHETIC_DATA_READINESS_CHECKLIST.md`

Run tests (with `EXCEPTIONS_LAKE_CONTRACT_REPO_PATH` set as above):

```powershell
python scripts/ci_check_contract_lock.py
python -m pytest
```

## Local CLI

After install, the local CLI is available:

```powershell
exceptions-lake health
exceptions-lake ingest-synthetic examples/synthetic_exception_event.json
exceptions-lake list-events
exceptions-lake build-pressure-candidate
exceptions-lake non-synthetic-preflight examples/non_synthetic_readiness.example.json
exceptions-lake refresh-contract-lock
```

The non-synthetic preflight command is dry-run only. It does not append events and it
does not permit real ingestion.

## Contract pinning

`contracts.lock.json` pins this runtime repo to a specific contract repo git SHA.

The loader reads the live contract repo SHA and fail-closes if it does not match the pinned `contract_sha`. This keeps local development aligned to one reviewed contract version instead of silently drifting.

This pin is a governance and reproducibility aid only. It does not make the runtime production-ready and it does not weaken any non-claims around synthetic scope, lack of connectors, or lack of canon mutation.

## Test behavior

Tests do not write into the authoritative contract repo.

Instead, the test suite copies required contract surfaces into a temporary git-backed fixture repo and validates runtime behavior there. This lets the tests prove:

- contract loading works
- contract pinning is enforced
- missing contract files fail closed
- ingestion is append-only
- audit records are append-only
- no canon mutation occurs

## Runtime data

Default local runtime data path:

```text
./runtime_data/
```

The runtime will reject a `runtime_data` path nested inside the contract repo root.
