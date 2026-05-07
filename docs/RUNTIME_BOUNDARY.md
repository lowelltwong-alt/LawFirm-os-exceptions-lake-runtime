# Runtime Boundary

Canonical machine name: `exceptions-lake-runtime-main`. Plane: evidence. Sibling repos: `LawFirm-os-semantic-substrate` (control plane) and `LawFirm-os-orchestrator` (execution plane). For full sibling-repo names and authority order across repos, see substrate `governance/CROSS_REPO_MAP.md`.

`exceptions-lake-runtime-main` is a separate runtime repository that consumes contracts from the **Law Firm OS Semantic Substrate** (canonical machine name `LawFirm-os-semantic-substrate`) contract repository (clone source configured locally or via `CONTRACT_ONTOLOGY_REPOSITORY` in CI).

## Contract repo vs runtime repo

The contract repo remains authoritative for:

- schema meaning
- lifecycle states
- mutation authority
- promotion authority
- registries
- validators
- governed boundary doctrine

This runtime repo may:

- load versioned contracts
- validate synthetic exception candidates
- store accepted synthetic runtime observations locally
- emit synthetic audit records
- derive non-canonical pressure-vector candidates in memory

Contract loading policy is manifest-first:

- the runtime consumes `registry/exceptions-lake-contract-export.json` first when present
- if that manifest is present but malformed, missing required fields, or referencing invalid paths, loading fails closed
- fallback loading is allowed only when the export manifest is absent
- when `contracts.lock.json` is present, it is validated as a strict lock contract and must include:
  - `contract_repo`
  - `contract_ref_type`
  - `contract_sha`
  - `generated_at`
  - `generated_by`
- missing or invalid lock fields fail closed and require `python scripts/update_contract_lock.py`

Exception validation policy is fail-closed against canonical route authority:

- unknown `event_class` values are rejected against the substrate canonical route registry
- `route.route_id` and `event_class` mismatches are rejected with explicit validation reasons
- validation metadata (including `schema_id` and validation errors) is preserved in runtime audit/evidence records
- runtime records remain observational evidence only and do not mutate canon

This runtime repo may not:

- redefine canonical semantics
- redefine lifecycle states
- redefine mutation rules
- redefine promotion authority
- mutate canon
- write into the contract repo path
- redefine ontology or governance semantics in local runtime docs or code

## Governed learning posture

Runtime observations are exception candidates only.

They may influence canon only through the governed path:

```text
exception-event -> pressure-vector -> adaptation-proposal -> promotion-decision
```

This MVP stops at a synthetic, non-canonical pressure-vector candidate.

## MVP non-claims

This repo does not implement:

- production event storage
- real connector workers
- dashboards
- deployment infrastructure
- live access enforcement
- production telemetry
- real firm operational data handling
