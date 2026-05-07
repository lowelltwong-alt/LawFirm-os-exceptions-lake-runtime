# Recent Work

## 2026-05-07 - Substrate Contract Lock Sync

- Refreshed `contracts.lock.json` to pin the currently released Semantic Substrate commit `43991155f0286e6d8bc5ba0bfe6b42407b1b3f12`.
- Updated current front-door references in `AGENTS.md`, `AI_TABLE_OF_CONTENTS.md`, `ENDPOINTS_AND_COMMANDS.md`, and `DATA_FLOW_MAP.md` so runtime lock documentation matches the attached substrate export.
- Contract surfaces between the older `d2ac7f504e67aa00985fbe53aa5350f940e8b529` pin and `43991155f0286e6d8bc5ba0bfe6b42407b1b3f12` were checked across manifest, registry, schema, governance, and front-door paths from the substrate repo; no contract-surface content drift was found.
- No schemas, route IDs, event classes, runtime authority, Research Radar automation, model calls, external APIs, external writes, Substrate writes, or canon promotion behavior were added.

## 2026-05-06 - Phase 2 Front-Door Documentation Completion

Codex task / PR: Final verification gap cleanup for root AI front-door docs.

Files changed:
- Added `AGENTS.md` with evidence-plane authority boundaries, required read order, current contract pin, data-flow pointer, and stop conditions.
- Added `AI_TABLE_OF_CONTENTS.md` with pointers to runtime boundary docs, current command surfaces, contract authority, data-flow map, and Phase 2 planned/current status.
- Added `ENDPOINTS_AND_COMMANDS.md` documenting the local CLI, local scripts, library facade, environment requirement, and no-production/no-external-write boundaries.

Schemas changed:
- None.

Contracts changed:
- None. `contracts.lock.json` unchanged.

Runtime behavior changed:
- None.

Risk color:
- Green. Documentation-only front-door completion.

Harness level:
- H0 documentation alignment plus existing validation.

## 2026-05-06 — Cross-Repo Coherence Patch 4: Substrate Identity Alignment

Codex task / PR: Cross-repo coherence fix train Patch 4 (evidence-lake side).

Files changed:
- Refreshed `contracts.lock.json` to pin the substrate at commit `d2ac7f504e67aa00985fbe53aa5350f940e8b529` (substrate Patch 1 + Patch 2). Replaced placeholder `your-org/law-firm-ontology` with canonical `LawFirm-os-semantic-substrate`. Renamed `generated_by` to canonical `exceptions-lake-runtime-main`. Added `contract_repo_human_label`, `manifest_first_loading` block, and an expanded `non_claims` list (live model calls, scheduled jobs, live research crawling, external APIs, external writes, invented route_id/event_class).
- Updated `scripts/update_contract_lock.py` to mirror the new lock format. The lock-refresh tool now writes the canonical substrate machine name, the canonical runtime name, the manifest-first loading block, and the expanded non_claims list.
- Updated `.github/workflows/ci.yml` to use the canonical substrate name in `CONTRACT_ONTOLOGY_REPOSITORY` (placeholder `your-org/LawFirm-os-semantic-substrate` with explicit fork-must-override comment) and to use `LawFirm-os-semantic-substrate` as the contract checkout path. Existing CI behavior preserved: lock sanity check, pin-aware checkout, pytest.
- Updated `docs/RUNTIME_BOUNDARY.md` with canonical names, sibling-repo reference, and `governance/CROSS_REPO_MAP.md` pointer at the substrate.
- Updated `docs/ai-workflow/runtime-route-table.yaml` `contract_authority` block to use canonical machine name `LawFirm-os-semantic-substrate` and canonical human label.
- Updated `docs/CANONICAL_ROUTE_MAPPING.md`, `docs/LOCAL_DEV.md`, `docs/RUNTIME_HANDOFF.md`, `docs/ai-workflow/README.md`, `docs/ai-workflow/contract-consumption-router.md`, `docs/ai-workflow/runtime-ai-work-cycle.md`, `docs/ai-workflow/runtime-audit-event-policy.md`, and `docs/ai-workflow/runtime-audit-capture-roadmap.md` to use the canonical substrate machine name and human label consistently.
- Updated `README.md` and `AI_WORK_START_HERE.md` with canonical names, sibling-repo reference, and `governance/CROSS_REPO_MAP.md` pointer at the substrate.
- Added `DATA_FLOW_MAP.md` describing evidence-plane data flow with Mermaid flowchart and sequence, substrate-consumption discipline, and pin-and-refresh requirements.

Schemas changed:
- None.

Commands/endpoints changed:
- None. CLI surface unchanged (`exceptions-lake health`, `ingest-synthetic`, `list-events`, `build-pressure-candidate`, `non-synthetic-preflight`, `refresh-contract-lock`).

Data flow changed:
- None at the runtime behavior level. Substrate identity normalized across all docs, lock, lock-refresh script, and CI.

Tests added/updated:
- None.

Risk color:
- Yellow. Identity-alignment change with no behavior change. Lock refresh requires the substrate commit to exist in substrate history at refresh time.

Hardness/harness level:
- H1 documentation/identity update plus existing validation.

Leverage rationale:
- Eliminates the five-name identity sprawl across repos. The runtime now consistently identifies the substrate as `LawFirm-os-semantic-substrate` with the canonical human label "Law Firm OS Semantic Substrate". The lock-refresh script will not regenerate the legacy placeholder.

Preserved invariants:
- append-only evidence-only posture
- fail-closed contract lock on SHA drift
- no canon mutation
- no promotion to canon
- no live model calls, scheduled jobs, external APIs, external writes, or live research crawling
- no invented `route_id` or `event_class`

Validation:
- `python scripts/ci_check_contract_lock.py` (read-only check)
- `python -m pytest`
- canonical-name grep audit
- canon-mutation prohibition grep audit
