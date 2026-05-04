# Runtime Audit Capture Roadmap

This roadmap defines the runtime path for AI interaction audit metadata while preserving the FMG contract-authority boundary.

## Current posture

This repo may support synthetic and dry-run audit metadata. It must not store production conversation text, real FMG records, credentials, secrets, or sealed transcript contents.

## Phase 0 — Docs-only boundary

- Define runtime audit routes.
- Define transcript and retention boundaries.
- State that FMG owns canonical audit contracts.
- Keep all changes docs-only.

## Phase 1 — Synthetic audit envelope

Future runtime work may capture synthetic or dry-run audit envelopes with:

- runtime route
- mode
- FMG contract SHA
- content hashes
- policy decision
- tool-call metadata
- local audit event hash

No production conversation text is allowed in this repo.

## Phase 2 — Contract-aligned audit schema consumption

After FMG publishes audit-event schemas, this runtime may validate synthetic audit envelopes against pinned FMG contracts.

## Phase 3 — Secure transcript-store integration planning

Plan, but do not implement, integration with an approved external secure audit store for sealed transcripts.

## Phase 4 — Production capture only after governance approval

Production AI interaction audit capture requires:

- approved FMG audit contracts
- secure external transcript store
- retention classification
- legal-hold workflow
- access controls
- privilege/confidentiality review
- explicit runtime implementation PR
