# AGENTS.md

<!-- BEGIN LAWFIRM_OS_BOOTSTRAP -->
Managed bootstrap for the LawFirm OS Skill-Agent Control Plane. This block adds cross-repo routing context; it must not replace the repo-specific instructions preserved below.

Before making changes in this repository, read:

1. AI_WORK_START_HERE.md
2. skill-agent-manifest.json
3. ../LawFirm-os-semantic-substrate/registry/ai-front-door-registry.json, or registry/ai-front-door-registry.json when already in Semantic Substrate
4. ../LawFirm-os-semantic-substrate/registry/skill-agent-control-plane-registry.json, or registry/skill-agent-control-plane-registry.json when already in Semantic Substrate
5. ../LawFirm-os-semantic-substrate/governance/SKILL_AGENT_CONTROL_PLANE_BOUNDARY.md, or local governance/SKILL_AGENT_CONTROL_PLANE_BOUNDARY.md in Semantic Substrate

Repo: LawFirm-os-exceptions-lake-runtime-main
Plane: evidence plane
Repo purpose: Append-only evidence, audit records, defects, retrieval traces, skill-agent events, and learning candidates.
This repo must not own: Canonical semantics, skill promotion authority, raw legal payload storage.

Preservation rule: keep the REPO_SPECIFIC_INSTRUCTIONS section intact unless a human explicitly approves removal. New bootstrap text should be merged around repo-specific doctrine, not overwrite it.
<!-- END LAWFIRM_OS_BOOTSTRAP -->

<!-- BEGIN REPO_SPECIFIC_INSTRUCTIONS -->
# AGENTS.md

## Required AI entry behavior

Before making changes in this repository, read:

1. `AI_WORK_START_HERE.md`
2. `../LawFirm-os-semantic-substrate/registry/ai-front-door-registry.json`
3. `../LawFirm-os-semantic-substrate/governance/AI_FRONT_DOOR_BOUNDARY.md`

This repository is one component of the LawFirm OS multi-repo kernel. Do not treat it as standalone.

## Boundary rule

This repository owns append-only runtime evidence, audit records, retrieval traces, defects, and lake validation surfaces only. It must not store full raw legal document payloads, define canonical schemas or route authority, or mutate Semantic Substrate meaning. Canonical contracts and the AI front door live in `LawFirm-os-semantic-substrate`.

## Required validation

Before reporting success, run `python -m pytest -q` in this repository (set `EXCEPTIONS_LAKE_CONTRACT_REPO_PATH` to your sibling substrate checkout when tests require it) and the AI front-door integrity gate: `python ../LawFirm-os-semantic-substrate/scripts/validate_ai_front_door.py --substrate-root ../LawFirm-os-semantic-substrate`.

## Canonical Names

- Substrate / control plane: `LawFirm-os-semantic-substrate`
- Orchestrator / execution plane: `LawFirm-os-orchestrator`
- Exception Lake / evidence plane: `exceptions-lake-runtime-main` (this repo)

For cross-repo authority order, read the substrate repo's `governance/CROSS_REPO_MAP.md`.

## Core Boundary

This repo is the evidence plane only. It validates and records append-only runtime/audit evidence. It consumes pinned Semantic Substrate contracts through `contracts.lock.json`.

It must not:

- define canonical schemas, route IDs, or event classes;
- mutate the Semantic Substrate;
- promote candidates to canon;
- create production connectors;
- ingest real client, matter, employee, or privileged data;
- run live Research Radar automation;
- call live models, crawlers, external APIs, or external write targets.

## Required Read Order

1. `README.md`
2. `AI_WORK_START_HERE.md`
3. `AI_TABLE_OF_CONTENTS.md`
4. `DATA_FLOW_MAP.md`
5. `ENDPOINTS_AND_COMMANDS.md`
6. `docs/RUNTIME_BOUNDARY.md`
7. `docs/CANONICAL_ROUTE_MAPPING.md`
8. `docs/LOCAL_DEV.md`
9. `RECENT_WORK.md`

## Current Contract Pin

`contracts.lock.json` points to:

- `contract_repo: LawFirm-os-semantic-substrate`
- `contract_sha: 43991155f0286e6d8bc5ba0bfe6b42407b1b3f12`
- `generated_by: exceptions-lake-runtime-main`

Tests that load contracts require `EXCEPTIONS_LAKE_CONTRACT_REPO_PATH` to point at a local sibling checkout of `LawFirm-os-semantic-substrate`.

## Data Flow Map

Use root `DATA_FLOW_MAP.md` as the evidence-plane map. It shows:

- control plane to Exception Lake contract flow;
- control plane to Orchestrator flow;
- Orchestrator to Exception Lake evidence packet flow;
- Exception Lake to human governance candidates;
- human-approved promotion back to the control plane;
- no direct runtime to canon mutation.

## Stop Immediately If

- a task asks this repo to mutate canon;
- a task asks this repo to promote candidates to canon;
- a task asks for invented `route_id` or `event_class` values;
- a task asks for real client or matter data;
- a task asks for live crawling, scheduled jobs, model calls, external APIs, or external writes;
- a task asks to bypass append-only runtime/audit record semantics.

<!-- END REPO_SPECIFIC_INSTRUCTIONS -->

## Skill-Agent Control Plane References

- skill-agent-manifest.json
- Semantic Substrate registry/skill-agent-control-plane-registry.json
- Semantic Substrate registry/skill-agent-graph-index.json
- Semantic Substrate registry/lawfirm-os-repo-registry.json
- Semantic Substrate governance/SKILL_AGENT_CONTROL_PLANE_BOUNDARY.md
- Semantic Substrate governance/SKILL_AGENT_LIFECYCLE_AND_RECURSIVE_IMPROVEMENT.md

## Validation Commands

    python -m pytest -q
    python ../LawFirm-os-semantic-substrate/scripts/validate_skill_agent_control_plane.py --workspace ..