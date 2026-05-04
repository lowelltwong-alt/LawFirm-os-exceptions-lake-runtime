# Contract Consumption Router

This runtime consumes FMG contracts. It does not own schema meaning, lifecycle states, mutation authority, or promotion authority.

## Contract authority

Authoritative contract repository:

```text
lowelltwong-alt/fmg-fractal-capability-ontology
```

Runtime work must identify whether it is:

- reading current pinned contracts
- refreshing a contract lock
- validating payloads against FMG schemas
- checking route registry behavior
- planning a future contract change that belongs in FMG

## Decision path

```text
Runtime task
  -> Does it change schema meaning?
      -> yes: stop; route to FMG contract repo
      -> no
  -> Does it consume a pinned FMG contract SHA?
      -> no: stop or refresh contract lock route
      -> yes
  -> Does it persist events?
      -> synthetic/local only in MVP
  -> Does it create adaptation proposals or promotion decisions?
      -> no in this runtime MVP
```

## Required runtime statement

Every runtime PR should state:

- FMG contract SHA or contract source behavior
- whether contract meaning changed
- whether runtime persistence changed
- whether audit behavior changed
- whether follow-up in FMG contract repo is required
