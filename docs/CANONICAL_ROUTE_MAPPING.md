# Canonical Route Mapping Contract

This document maps runtime-local route and action labels in this repository to Substrate canonical route authority.

Authoritative Law Firm OS Semantic Substrate sources (paths relative to your contract checkout, e.g. `LawFirm-os-semantic-substrate/`):

- `LawFirm-os-semantic-substrate/registry/exception-route-registry.json`
- `LawFirm-os-semantic-substrate/registry/exceptions-lake-contract-export.json`
- `LawFirm-os-semantic-substrate/governance/EXCEPTIONS_LAKE_BOUNDARY.md`
- `LawFirm-os-semantic-substrate/governance/EXCEPTIONS_LAKE_ARCHITECTURE.md`

## Boundary rule

Runtime route labels in this repo are operational workflow labels for local development and planning. They are not canonical truth.

Canonical route meaning is defined only by Law Firm OS Semantic Substrate `route_id` + `event_class` values. Runtime observations remain evidence and may become exception candidates only; they do not directly mutate canon.

## Substrate canonical route authority (current)

- `route.retrieval_miss.v1` -> `event_class: retrieval_miss`
- `route.workflow_escalation.v1` -> `event_class: workflow_escalation`
- `route.authority_conflict_override.v1` -> `event_class: authority_conflict_override`

Canonical raw actions (from the Law Firm route registry):

- allowed raw actions: `route_for_review`, `aggregate_pressure`, `attach_evidence_only`
- prohibited direct actions: `canonical_ontology_write`, `taxonomy_rewrite`, `schema_mutation`, `policy_overwrite`, `address_system_mutation`

## Runtime Route Label Mapping

All route labels currently defined in `docs/ai-workflow/runtime-route-table.yaml` are mapped below.

| Runtime route label | Runtime scope | Canonical mapping status | Canonical route_id | Canonical event_class | Notes |
|---|---|---|---|---|---|
| `health_check` | runtime health/readiness | Unmapped (non-exception operational route) | TBD | TBD | Local operational route; no canonical exception class bound. |
| `synthetic_exception_ingest` | synthetic exception ingest | Partially mapped | `route.retrieval_miss.v1` or `route.workflow_escalation.v1` or `route.authority_conflict_override.v1` | `retrieval_miss` or `workflow_escalation` or `authority_conflict_override` | Runtime label is generic; canonical mapping depends on payload `event_class`. |
| `contract_lock_refresh` | contract pin maintenance | Unmapped (contract maintenance route) | TBD | TBD | Local maintenance route, not a canonical exception route. |
| `non_synthetic_dry_run_preflight` | metadata-only readiness check | Unmapped (preflight route) | TBD | TBD | Preflight and audit planning flow, no canonical exception class emitted by default. |
| `audit_event_review` | runtime audit metadata review | Unmapped (governance support route) | TBD | TBD | Review/planning route; canonical route applies only when an exception event is emitted. |
| `event_store_review` | append-only store review | Unmapped (storage review route) | TBD | TBD | Operational review route, not a canonical route ID. |
| `pressure_candidate_build` | pressure candidate planning/build | Partially mapped | TBD | TBD | Uses pressure concepts but no canonical route ID unless sourced from mapped exception events. |
| `future_connector_planning` | future connector planning | Unmapped (future planning route) | TBD | TBD | Explicitly planning-only. |
| `future_ai_interaction_audit_planning` | future audit planning | Unmapped (future planning route) | TBD | TBD | Planning-only and non-canonical. |

## Runtime Action Label Mapping

This section maps route/action labels used in runtime workflow docs to Substrate canonical action authority where applicable.

| Runtime action label | Canonical mapping status | Substrate canonical action | Notes |
|---|---|---|---|
| `synthetic_exception_ingest` | Partially mapped | `route_for_review` | Canonical when a valid exception event is routed for review. |
| `pressure_candidate_build` | Partially mapped | `aggregate_pressure` | Canonical only if built from governed exception evidence. |
| `audit_event_review` | Mapped (evidence handling) | `attach_evidence_only` | Applies when attaching review evidence without mutation authority. |
| `health_check` | Unmapped/TBD | TBD | Operational check, not a canonical exception action. |
| `contract_lock_refresh` | Unmapped/TBD | TBD | Contract maintenance operation. |
| `non_synthetic_dry_run_preflight` | Unmapped/TBD | TBD | Readiness preflight, not canonical exception routing. |
| `event_store_review` | Unmapped/TBD | TBD | Storage review operation. |
| `future_connector_planning` | Unmapped/TBD | TBD | Planning operation. |
| `future_ai_interaction_audit_planning` | Unmapped/TBD | TBD | Planning operation. |

## Required Runtime Interpretation

1. Runtime routes are implementation labels.
2. Law Firm OS Semantic Substrate `route_id` and `event_class` are canonical authority.
3. If runtime emits/handles exception events, the payload must use one of the Substrate canonical `event_class` values and be validated against the Law Firm route registry.
4. Unmapped/TBD entries here are intentionally non-canonical runtime operations and must not be treated as canonical route IDs.
