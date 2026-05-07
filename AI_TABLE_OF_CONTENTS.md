# AI Table Of Contents

Canonical machine name: `exceptions-lake-runtime-main`. Plane: evidence.

This repo owns append-only runtime/audit evidence support. It consumes contracts from `LawFirm-os-semantic-substrate` and must not mutate or promote canon.

## Start Here

- `AI_WORK_START_HERE.md` - runtime-specific AI work router.
- `AGENTS.md` - agent-facing safety and authority rules.
- `README.md` - current MVP scope, CLI, setup, and safety posture.
- `RECENT_WORK.md` - latest local changes and validation notes.
- `DATA_FLOW_MAP.md` - Mermaid-ready evidence-plane data flow map.

## Runtime Boundary

- `docs/RUNTIME_BOUNDARY.md` - evidence-plane boundary.
- `docs/RUNTIME_HANDOFF.md` - orchestrator/runtime handoff notes.
- `docs/CANONICAL_ROUTE_MAPPING.md` - maps local runtime labels to substrate canonical route authority.
- `docs/NON_SYNTHETIC_DATA_READINESS_CHECKLIST.md` - metadata-only readiness guardrails.
- `docs/LOCAL_DEV.md` - local development and contract path setup.

## Commands And Local Surfaces

- `ENDPOINTS_AND_COMMANDS.md` - current CLI commands and local checks.
- `src/exceptions_lake_runtime/cli.py` - CLI parser.
- `src/exceptions_lake_runtime/api.py` - library facade.
- `scripts/ci_check_contract_lock.py` - read-only lock-shape guardrail.
- `scripts/update_contract_lock.py` - explicit local lock refresh tool; writes only this repo's `contracts.lock.json` when intentionally run.

## Contract Authority

`contracts.lock.json` currently pins:

- `contract_repo: LawFirm-os-semantic-substrate`
- `contract_sha: d2ac7f504e67aa00985fbe53aa5350f940e8b529`
- `generated_by: exceptions-lake-runtime-main`

The runtime consumes substrate contracts read-only. Canonical `route_id` and `event_class` authority belongs to the substrate.

## Phase 2 Status

Current:

- append-only event store
- append-only audit log
- synthetic exception-event validation
- route/event-class fail-closed validation against substrate contracts
- synthetic pressure-vector candidate builder
- non-synthetic dry-run preflight metadata check

Planned or not implemented here:

- Phase 2 opportunity, autonomy, harness, research, and decision records are not production runtime surfaces in this repo unless separately implemented and validated.
- Research Radar automation is not implemented.
- Promotion to canon is not implemented and is not allowed in this repo.

## Hard Boundaries

- no canon mutation
- no promotion to canon
- no invented route IDs or event classes
- no live Research Radar automation
- no live web crawling
- no scheduled jobs
- no live model calls
- no external API calls
- no external writes
- no real client or matter data
