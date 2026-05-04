# Non-Synthetic Data Readiness Checklist

This runtime is still a non-production MVP. Real events are still forbidden in this repository unless a later PR explicitly changes that boundary.

## What is allowed here now

- synthetic exception-event ingestion
- contract validation
- append-only local synthetic event storage
- append-only local audit logging
- non-canonical pressure-vector candidate generation
- metadata-only non-synthetic dry-run preflight

## What is not allowed in this PR

- real event ingestion
- live connector code
- dashboards
- deployment secrets or production config
- canon mutation

## Non-synthetic readiness requirements

Before any future non-synthetic source can even enter a dry-run preflight, the runtime expects metadata for:

- source name and source system type
- source-ingestion manifest identifier plus manifest path or reference
- data classification and sensitivity level
- allowed-use basis
- retention rule
- access owner
- business owner
- validation owner
- explicit dry-run approval status
- rollback or quarantine plan
- evidence provenance availability
- contract SHA

## Ownership and approval posture

Non-synthetic readiness is not just a technical check. It also requires explicit business, security, and governance ownership before any later PR considers real-data admission.

This runtime currently encodes that expectation as:

- `business_owner`
- `access_owner`
- `validation_owner`
- `approval_status == approved_for_dry_run`

## Dry-run only

The supported future envelope mode is:

```text
non_synthetic_dry_run_preflight
```

That mode:

- runs metadata readiness checks only
- may write a dry-run audit record
- may not append events
- may not persist non-synthetic source data
- may not bypass deny-by-default policy

## First connector boundary

The first live connector must be proposed and scoped in a later PR. It is intentionally out of scope here.
