# Runtime Boundary

`exceptions-lake-runtime` is a separate runtime repository that consumes contracts from `lowelltwong-alt/fmg-fractal-capability-ontology`.

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
- real FMG data handling
