# AI Work Start Here

Canonical machine name: `exceptions-lake-runtime-main`. Plane: evidence. Sibling repos: `LawFirm-os-semantic-substrate` (control plane), `LawFirm-os-orchestrator` (execution plane). For authority order across repos, see substrate `governance/CROSS_REPO_MAP.md`.

This is the runtime-specific AI work router for `exceptions-lake-runtime-main`.

## Required read order

Before AI-assisted edits, read:

1. `README.md`
2. `docs/RUNTIME_BOUNDARY.md`
3. `docs/LOCAL_DEV.md`
4. `docs/RUNTIME_HANDOFF.md`
5. `docs/NON_SYNTHETIC_DATA_READINESS_CHECKLIST.md`
6. this file
7. the route table under `docs/ai-workflow/runtime-route-table.yaml`

## Runtime boundary

This repo consumes versioned contracts from the Law Firm OS Semantic Substrate contract repository.

It does not redefine schema meaning, lifecycle states, mutation authority, or promotion authority. Runtime observations may become exception candidates only. Canonical change still requires the governed ontology path:

```text
exception-event -> pressure-vector -> adaptation-proposal -> promotion-decision
```

## Universal runtime work cycle

1. Orient
2. Confirm contract authority
3. Classify runtime task
4. Choose mode: Explore / Plan / Edit / Execute
5. Select route
6. Apply stop conditions
7. Execute inside scope
8. Validate with `pytest`
9. Open PR
10. Report outcome and audit impact

## AI interaction audit principle

This repo may plan or implement synthetic/dry-run audit events. It must not store raw production conversation content. Production audit capture requires approved governed contracts and an external secure audit store.

## Hard stop

Stop if contract SHA, schema version, policy boundary, source type, persistence behavior, or audit behavior is ambiguous.
