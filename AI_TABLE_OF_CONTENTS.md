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
- `docs/INTAKE_LAKE_ADMISSION_REVIEW.md` - candidate-only intake budget, carrier rejection, appeal, and actuals evidence admission review docket.
- `docs/LOCAL_DEV.md` - local development and contract path setup.
- `.ai/control/governance-dependency-map-mirror.json` - local mirror of the upstream governance dependency map; it cannot override `LawFirm-os-semantic-substrate`.
- `scripts/validate_governance_dependency_map_mirror.py` - fail-closed check for mirror shape and watched governance paths.

## Commands And Local Surfaces

- `ENDPOINTS_AND_COMMANDS.md` - current CLI commands and local checks.
- `src/exceptions_lake_runtime/cli.py` - CLI parser.
- `src/exceptions_lake_runtime/api.py` - library facade.
- `scripts/ci_check_contract_lock.py` - read-only lock-shape guardrail.
- `scripts/update_contract_lock.py` - explicit local lock refresh tool; writes only this repo's `contracts.lock.json` when intentionally run.
- `config/validation-runtime-policy.yaml` - minimum runtime ceiling policy for full and focused pytest validation.
- `scripts/run_full_pytest.py` - required pytest wrapper that applies the validation runtime policy marker and long timeout.
- `scripts/validate_intake_lake_admission_review.py` - deterministic validator for the candidate intake Lake admission docket.
- `registry/intake-lake-admission-review-registry.json` - local candidate-only registry for budget evidence mapping and carrier rejection admission planning.

## Contract Authority

`contracts.lock.json` currently pins:

- `contract_repo: LawFirm-os-semantic-substrate`
- `contract_sha: 43991155f0286e6d8bc5ba0bfe6b42407b1b3f12`
- `generated_by: exceptions-lake-runtime-main`

The runtime consumes substrate contracts read-only. Canonical `route_id` and `event_class` authority belongs to the substrate.
The runtime also checks Substrate `registry/governance-dependency-map.json` when governance-facing evidence-plane files change.

## AI Strategy and Context Quality Runtime Evidence

- Exception Lake records context defects, reviewer corrections, calibration evidence, drift evidence, and pressure vectors as runtime evidence only.
- It does not mutate Semantic Substrate canon.
- Legal Context Bundle outcomes and context-quality events are evidence, not authority.
- Shannon/entropy metrics must be treated as measurement evidence, not legal truth.
- Future richer context-quality event surfaces must wait for Semantic Substrate schemas and Exception Lake adoption.

## Phase 2 Status

Current:

- append-only event store
- append-only audit log
- synthetic exception-event validation
- route/event-class fail-closed validation against substrate contracts
- synthetic pressure-vector candidate builder
- non-synthetic dry-run preflight metadata check
- candidate-only intake Lake admission docket for budget changes, carrier rejections, appeals, outcomes, and actuals comparison
- deterministic pytest runtime policy requiring `python scripts/run_full_pytest.py`

Planned or not implemented here:

- default intake/carrier writes to the Lake are not implemented.
- SQLite migrations for intake/carrier records are not implemented.
- carrier portal or email connector capture is not implemented.
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
