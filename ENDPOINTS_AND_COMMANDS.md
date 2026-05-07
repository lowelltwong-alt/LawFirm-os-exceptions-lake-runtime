# Endpoints And Commands

This repo has no HTTP endpoint, production service, dashboard, production connector, live Research Radar automation, scheduled job, live model-call surface, or external write surface.

All current surfaces are local library calls, local CLI commands, and local validation scripts.

## Environment

Most runtime commands that load contracts require:

```powershell
$env:EXCEPTIONS_LAKE_CONTRACT_REPO_PATH = 'C:\path\to\LawFirm-os-semantic-substrate'
```

The current lock points to substrate commit `43991155f0286e6d8bc5ba0bfe6b42407b1b3f12`.

## CLI

Installed script entrypoint:

```powershell
exceptions-lake <command>
```

Module source: `src/exceptions_lake_runtime/cli.py`.

### health

```powershell
exceptions-lake health
```

Purpose: report local runtime health and contract availability.

### ingest-synthetic

```powershell
exceptions-lake ingest-synthetic examples/synthetic_exception_event.json
```

Purpose: validate and append a synthetic exception event plus audit record.

Controls:

- accepts only raw synthetic exception-event payloads or `synthetic_test_only` envelopes;
- validates against pinned substrate contracts;
- fails closed on unknown `route_id` or `event_class`;
- writes append-only local event/audit records only.

### list-events

```powershell
exceptions-lake list-events
```

Purpose: list locally stored runtime events.

### build-pressure-candidate

```powershell
exceptions-lake build-pressure-candidate
```

Purpose: build a non-canonical pressure-vector candidate from stored evidence. This is candidate evidence only and does not create an adaptation proposal or promotion decision.

### non-synthetic-preflight

```powershell
exceptions-lake non-synthetic-preflight examples/non_synthetic_readiness.example.json
```

Purpose: run a metadata-only dry-run readiness check. It does not persist real events and does not authorize live connector or production use.

### refresh-contract-lock

```powershell
exceptions-lake refresh-contract-lock
```

Purpose: explicit local maintenance command that runs `scripts/update_contract_lock.py` and writes this repo's `contracts.lock.json`. It must be used only when intentionally refreshing the reviewed substrate pin.

## Scripts

```powershell
python scripts/ci_check_contract_lock.py
python scripts/update_contract_lock.py
python -m pytest
```

`ci_check_contract_lock.py` is read-only. `update_contract_lock.py` writes only this repo's `contracts.lock.json` and must not be used as an implicit runtime behavior.

## API Surface

The library facade is in `src/exceptions_lake_runtime/api.py` and supports local health, synthetic ingest, event listing, pressure-candidate building, and non-synthetic preflight helpers.

The API is evidence-plane only:

- no canon mutation
- no promotion to canon
- no production connector writes
- no external APIs
- no external writes
- no live model calls
- no live Research Radar automation

## Data Flow

See `DATA_FLOW_MAP.md` for the evidence-plane flow from substrate contracts and orchestrator evidence packets into append-only event/audit records and human-governance candidates.
