# AGENTS.md

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
- `contract_sha: d2ac7f504e67aa00985fbe53aa5350f940e8b529`
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
