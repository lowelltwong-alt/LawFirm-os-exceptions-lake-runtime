# exceptions-lake-runtime

Canonical machine name: `exceptions-lake-runtime-main`. Human label: Law Firm OS Exceptions Lake Runtime. Plane: evidence. Sibling repos: `LawFirm-os-semantic-substrate` (control plane), `LawFirm-os-orchestrator` (execution plane). For sibling-repo names and authority order across repos, see substrate `governance/CROSS_REPO_MAP.md`.

`exceptions-lake-runtime-main` is a library-first, non-production MVP runtime skeleton for governed Exceptions Lake processing.

It consumes versioned contracts from the authoritative **Law Firm OS Semantic Substrate** (canonical machine name `LawFirm-os-semantic-substrate`) (contract) repository.

- **CI default:** the clone source is the `CONTRACT_ONTOLOGY_REPOSITORY` environment variable in [`.github/workflows/ci.yml`](.github/workflows/ci.yml) (set to a public ontology slug for reproducible builds).
- **Local development:** set `EXCEPTIONS_LAKE_CONTRACT_REPO_PATH` to your checkout of that contract repository (any path; see `docs/LOCAL_DEV.md`).

This repo does not redefine schema meaning, lifecycle states, mutation authority, or promotion authority. Runtime observations may become exception candidates only. Canonical change still requires the governed path:

```text
exception-event -> pressure-vector -> adaptation-proposal -> promotion-decision
```

## What this MVP does

This MVP proves one safe synthetic flow:

```text
synthetic exception candidate
-> deny-by-default policy check
-> contract validation
-> append-only local event store
-> append-only local audit log
-> synthetic pressure-vector candidate in memory only
```

It also supports a metadata-only future readiness surface:

```text
non_synthetic_dry_run_preflight
-> readiness check only
-> audit-only dry run result
-> no event persistence
```

Implemented surfaces:

- contract loading from a local contract repo path
- contract pinning via `contracts.lock.json`
- JSON Schema validation for synthetic `exception-event` payloads
- route-registry checks for governed exception intake
- deny-by-default runtime policy gate
- append-only local JSONL event store
- append-only local JSONL audit log
- in-memory synthetic pressure-vector candidate builder
- pure Python facade for health, ingest, and list operations
- local CLI for synthetic runtime operations and dry-run preflight

## What this MVP is not

This repo is not:

- a production runtime
- a deployment package
- a dashboard system
- a connector implementation repo
- a source of canonical semantic truth
- a canon mutation engine

It does not include:

- real firm operational data
- real clients, matters, employees, policies, or incidents
- Litify, BillBlast, iManage, portal, AR, SharePoint, or Excel connectors
- deployment secrets or cloud configuration
- production telemetry
- FastAPI or an HTTP service surface

HTTP is intentionally out of scope for this first implementation so we can keep the MVP small, library-first, and easy to validate locally.

## Pre-PR checklist (local-first, mirrors CI)

1. `python -m pip install -e ".[dev]"`
2. `python scripts/ci_check_contract_lock.py`
3. Point `EXCEPTIONS_LAKE_CONTRACT_REPO_PATH` at a local git checkout of the Law Firm OS Semantic Substrate contract repository (tests copy contract surfaces into a temporary fixture and temporarily align the lock to that fixture’s SHA; see `docs/LOCAL_DEV.md`).
4. `python -m pytest`

GitHub Actions runs the same sequence: lock check, shallow checkout of the public Law Firm OS Semantic Substrate contract repository at the pinned SHA, then `pytest`. No production services and no firm data.

## Local setup

1. Clone or otherwise obtain a local checkout of your Law Firm OS Semantic Substrate contract repository (example slug: `your-org/LawFirm-os-semantic-substrate`) on the branch or SHA you want the runtime to consume.
2. Set the contract repo path:

```powershell
$env:EXCEPTIONS_LAKE_CONTRACT_REPO_PATH = 'C:\path\to\LawFirm-os-semantic-substrate'
```

3. Install the runtime repo in editable mode:

```powershell
python -m pip install -e ".[dev]"
```

4. Run tests:

```powershell
pytest
```

5. Refresh the contract pin when you intentionally move to a new contract-repo SHA:

```powershell
python scripts/update_contract_lock.py
```

## Local CLI

After installing the repo in editable mode, you can use the local CLI:

```powershell
exceptions-lake health
exceptions-lake ingest-synthetic examples/synthetic_exception_event.json
exceptions-lake list-events
exceptions-lake build-pressure-candidate
exceptions-lake non-synthetic-preflight examples/non_synthetic_readiness.example.json
exceptions-lake refresh-contract-lock
```

The readiness example is metadata-only and dry-run-only. Replace
`contract_sha` with the currently pinned contract SHA before expecting a ready result.

## Contract consumption

The loader prefers `registry/exceptions-lake-contract-export.json` when it exists in the contract repo. If it is absent, the runtime falls back to the current-main contract surfaces:

- `registry/schema-registry.json`
- `registry/exceptions-schema-registry.json`
- `registry/governed-learning-schema-registry.json`
- `registry/exception-route-registry.json`
- `schemas/exception-event.schema.json`
- `schemas/pressure-vector.schema.json`
- `schemas/adaptation-proposal.schema.json`
- `schemas/promotion-decision.schema.json`
- `schemas/source-ingestion-manifest.schema.json`
- `schemas/access-decision.schema.json`
- `governance/EXCEPTIONS_LAKE_BOUNDARY.md`
- `governance/AI_CONTROL_PLANE_BOUNDARY.md`

The runtime also reads `contracts.lock.json` when present and fail-closes if the live contract repo SHA does not match the pinned SHA. This pins the synthetic MVP to one reviewed contract version and makes contract drift explicit for local development.

Runtime route/action labels are mapped to Law Firm canonical route authority in:

- `docs/CANONICAL_ROUTE_MAPPING.md`

## Safety posture

- deny by default
- allow synthetic/test envelopes only
- never write into the contract repo path
- never mutate canon
- never create adaptation proposals in MVP
- never create promotion decisions in MVP

Contract pinning does not create production readiness. It only makes the synthetic MVP more explicit about which reviewed contract version it is consuming.

See:

- `docs/RUNTIME_BOUNDARY.md`
- `docs/LOCAL_DEV.md`
- `docs/RUNTIME_HANDOFF.md`
- `docs/CANONICAL_ROUTE_MAPPING.md`
- `docs/NON_SYNTHETIC_DATA_READINESS_CHECKLIST.md`
- `docs/NEXT_CONNECTORS.md`

---

## Relationship to Law Firm OS Semantic Substrate repository

This repo should be understood as a runtime/application layer connected to the **Law Firm OS Semantic Substrate** (canonical machine name `LawFirm-os-semantic-substrate`) contract repository (for example a checkout named `LawFirm-os-semantic-substrate` on disk).

The Law Firm OS Semantic Substrate repository is the governing source of truth for:

- terminology
- governance concepts
- exception categories
- agent policy
- semantic layer design
- roadmap alignment

This repo should implement, test, or simulate those concepts without redefining them.
