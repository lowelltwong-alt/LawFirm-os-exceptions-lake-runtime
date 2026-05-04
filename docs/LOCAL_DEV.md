# Local Development

## Prerequisites

- Python 3.11+
- git (to create the local pinned contract checkout below)

## Create local pinned checkout (required for full pytest)

`EXCEPTIONS_LAKE_CONTRACT_REPO_PATH` must point at a git checkout whose `HEAD` SHA exactly
matches `contract_sha` in `contracts.lock.json`. Pointing at the live FMG repo fails whenever
its HEAD has moved past the pinned SHA.

Run once from the **runtime repo root** to create or refresh the pinned checkout:

**PowerShell**

```powershell
$SHA = (Get-Content contracts.lock.json | ConvertFrom-Json).contract_sha
New-Item -ItemType Directory -Force -Path ..\.ci-contracts | Out-Null
if (-not (Test-Path ..\.ci-contracts\fmg-fractal-capability-ontology-pinned)) {
    git clone https://github.com/lowelltwong-alt/fmg-fractal-capability-ontology `
        ..\.ci-contracts\fmg-fractal-capability-ontology-pinned
}
git -C ..\.ci-contracts\fmg-fractal-capability-ontology-pinned fetch origin
git -C ..\.ci-contracts\fmg-fractal-capability-ontology-pinned checkout $SHA
$env:EXCEPTIONS_LAKE_CONTRACT_REPO_PATH = (Resolve-Path ..\.ci-contracts\fmg-fractal-capability-ontology-pinned).Path
```

The pinned path (`..\.ci-contracts\fmg-fractal-capability-ontology-pinned`) sits outside the
runtime repo directory and is never committed. Re-run this block whenever `contracts.lock.json`
is updated to a new SHA.

## CI-equivalent command sequence (local-first)

Run these in order from the **runtime repo root** so your machine matches `.github/workflows/ci.yml`.
Create the pinned checkout first (see above). Do not substitute the live FMG repo unless its
HEAD exactly matches `contract_sha` in `contracts.lock.json`.

**PowerShell**

```powershell
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
python scripts/ci_check_contract_lock.py
$env:EXCEPTIONS_LAKE_CONTRACT_REPO_PATH = (Resolve-Path ..\.ci-contracts\fmg-fractal-capability-ontology-pinned).Path
python -m pytest
```

**Bash**

```bash
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
python scripts/ci_check_contract_lock.py
export EXCEPTIONS_LAKE_CONTRACT_REPO_PATH="$(realpath ../.ci-contracts/fmg-fractal-capability-ontology-pinned)"
python -m pytest
```

Tests copy contract files from the pinned checkout into a temporary git-backed fixture and
temporarily repin `contracts.lock.json` to that fixture's `HEAD` SHA. CI checks out the
public FMG ontology at the same pinned SHA for identical, reproducible fixtures (no firm data).

## Setup

Set the contract repo path to the pinned checkout (do not use the live FMG repo unless its
HEAD exactly matches `contract_sha` in `contracts.lock.json`):

```powershell
$env:EXCEPTIONS_LAKE_CONTRACT_REPO_PATH = (Resolve-Path '..\.ci-contracts\fmg-fractal-capability-ontology-pinned').Path
```

Install the runtime repo:

```powershell
python -m pip install -e ".[dev]"
```

Refresh the contract pin when you intentionally adopt a new contract repo SHA:

```powershell
python scripts/update_contract_lock.py
```

After updating the lock, re-run the pinned checkout block above so the local checkout moves
to the new SHA before running tests.

See also:

- `docs/RUNTIME_HANDOFF.md`
- `docs/NON_SYNTHETIC_DATA_READINESS_CHECKLIST.md`

Run tests (with `EXCEPTIONS_LAKE_CONTRACT_REPO_PATH` pointing at the pinned checkout):

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

The loader reads the live contract repo SHA and fail-closes if it does not match the pinned
`contract_sha`. This keeps local development aligned to one reviewed contract version instead
of silently drifting.

Pointing `EXCEPTIONS_LAKE_CONTRACT_REPO_PATH` at the pinned checkout ensures the SHA check
passes before any test fixture repinning takes effect, which is the same guarantee CI gets
by checking out at the exact pinned SHA.

This pin is a governance and reproducibility aid only. It does not make the runtime
production-ready and it does not weaken any non-claims around synthetic scope, lack of
connectors, or lack of canon mutation.

## Test behavior

Tests do not write into the authoritative contract repo.

Instead, the test suite copies required contract surfaces into a temporary git-backed fixture
repo and validates runtime behavior there. This lets the tests prove:

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
