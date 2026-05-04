# Contract Consumption Router

This runtime consumes Law Firm ontology contracts. It does not own schema meaning, lifecycle states, mutation authority, or promotion authority.

## Contract authority

Authoritative contract repository slug (configure in CI via `CONTRACT_ONTOLOGY_REPOSITORY`; locally use `EXCEPTIONS_LAKE_CONTRACT_REPO_PATH`):

```text
your-org/law-firm-ontology   # example; see .github/workflows/ci.yml for CI default
```

Runtime work must identify whether it is:

- reading current pinned contracts
- refreshing a contract lock
- validating payloads against Law Firm ontology schemas
- checking route registry behavior
- planning a future contract change that belongs in the Law Firm ontology repository

## Decision path

```text
Runtime task
  -> Does it change schema meaning?
      -> yes: stop; route to Law Firm ontology contract repo
      -> no
  -> Does it consume a pinned Law Firm contract SHA?
      -> no: stop or refresh contract lock route
      -> yes
  -> Does it persist events?
      -> synthetic/local only in MVP
  -> Does it create adaptation proposals or promotion decisions?
      -> no in this runtime MVP
```

## Required runtime statement

Every runtime PR should state:

- Law Firm contract SHA or contract source behavior
- whether contract meaning changed
- whether runtime persistence changed
- whether audit behavior changed
- whether follow-up in the Law Firm ontology contract repo is required
