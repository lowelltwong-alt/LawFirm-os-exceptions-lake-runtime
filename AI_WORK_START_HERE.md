# AI_WORK_START_HERE.md

<!-- BEGIN LAWFIRM_OS_BOOTSTRAP -->
Managed bootstrap for AI-assisted work in the LawFirm OS multi-repo workspace. Route through the canonical AI front door and Skill-Agent Control Plane, but preserve local repo operating doctrine.

Required bootstrap read order:

1. AGENTS.md
2. skill-agent-manifest.json
3. Semantic Substrate registry/ai-front-door-registry.json
4. Semantic Substrate registry/skill-agent-control-plane-registry.json
5. Semantic Substrate governance/SKILL_AGENT_CONTROL_PLANE_BOUNDARY.md

Repo: LawFirm-os-exceptions-lake-runtime-main
Plane: evidence plane
Repo purpose: Append-only evidence, audit records, defects, retrieval traces, skill-agent events, and learning candidates.
This repo must not own: Canonical semantics, skill promotion authority, raw legal payload storage.

Run workspace preservation and control-plane validation before reporting success on managed patch work.
<!-- END LAWFIRM_OS_BOOTSTRAP -->

<!-- BEGIN REPO_SPECIFIC_INSTRUCTIONS -->
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

<!-- END REPO_SPECIFIC_INSTRUCTIONS -->

## Skill-Agent Control Plane References

- skill-agent-manifest.json
- Semantic Substrate registry/skill-agent-control-plane-registry.json
- Semantic Substrate registry/skill-agent-lifecycle-policy-registry.json
- Semantic Substrate registry/skill-agent-quality-scoring-registry.json
- Semantic Substrate scripts/validate_skill_agent_control_plane.py

## Validation Commands

    python -m pytest -q
    python ../LawFirm-os-semantic-substrate/scripts/validate_skill_agent_control_plane.py --workspace ..