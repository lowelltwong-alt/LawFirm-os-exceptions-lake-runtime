# Runtime AI Workflow Router

This folder defines the AI-assisted work router for `exceptions-lake-runtime-main`.

This repo is a runtime consumer of contracts from the **Law Firm OS Semantic Substrate** (canonical machine name `LawFirm-os-semantic-substrate`) contract repository (clone source: see `CONTRACT_ONTOLOGY_REPOSITORY` in `.github/workflows/ci.yml` or your local checkout). It does not own canonical meaning, lifecycle states, mutation authority, or promotion authority.

## Entry point

Start with `AI_WORK_START_HERE.md` at the repository root.

## Core files

- `runtime-ai-work-cycle.md` — runtime-specific work cycle.
- `runtime-route-table.yaml` — machine-readable runtime route table.
- `runtime-stop-conditions.md` — stop conditions for runtime work.
- `contract-consumption-router.md` — how runtime work consumes Law Firm OS Semantic Substrate contracts.
- `runtime-audit-capture-roadmap.md` — roadmap for synthetic and future production audit capture.
- `runtime-audit-event-policy.md` — audit event capture principles.
- `runtime-transcript-retention-boundary.md` — transcript and retention boundary.

## Current posture

Docs-only. No live connectors, no production audit lake, no raw transcript storage, no real firm operational data, and no schema authority changes.
