# Runtime AI Work Cycle

All AI-assisted work in this runtime repo must preserve the contract-consumer boundary with the **Law Firm ontology** contract repository (see `CONTRACT_ONTOLOGY_REPOSITORY` in `.github/workflows/ci.yml` and `EXCEPTIONS_LAKE_CONTRACT_REPO_PATH` locally).

## Cycle

1. **Orient** — read `README.md`, runtime boundary docs, local dev docs, and `AI_WORK_START_HERE.md`.
2. **Confirm contract authority** — identify the Law Firm contract repo path and pinned contract SHA when relevant.
3. **Classify runtime task** — select a route from `runtime-route-table.yaml`.
4. **Choose mode** — Explore, Plan, Edit, or Execute.
5. **Apply stop conditions** — stop on ambiguous schema, contract SHA, persistence, or audit behavior.
6. **Execute inside scope** — keep work synthetic/dry-run unless explicitly authorized later.
7. **Validate** — run `pytest` for code-impacting changes.
8. **Open PR** — include contract and audit impact sections.
9. **Report outcome** — list files changed, validation, contract impact, and follow-up work.

## Runtime modes

| Mode | Meaning | Allowed side effects |
|---|---|---|
| Explore | Inspect runtime code/docs and contract consumption surfaces. | None |
| Plan | Propose runtime or connector work. | Docs-only |
| Edit | Change docs or approved MVP runtime code. | Repo-only |
| Execute | Run local synthetic/dry-run commands. | Local synthetic only |

No live connector, production audit capture, raw transcript capture, or real firm operational data handling is authorized by this router.
