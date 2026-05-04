# Local Development

## Prerequisites

- Python 3.11+
- a local checkout of `lowelltwong-alt/fmg-fractal-capability-ontology`

## Setup

Set the contract repo path:

```powershell
$env:EXCEPTIONS_LAKE_CONTRACT_REPO_PATH = 'C:\path\to\fmg-fractal-capability-ontology'
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

Run tests:

```powershell
pytest
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
