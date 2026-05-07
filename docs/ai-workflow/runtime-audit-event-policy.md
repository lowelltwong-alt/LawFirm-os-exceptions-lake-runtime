# Runtime Audit Event Policy

This policy defines how runtime audit metadata should be handled in this MVP repo.

## Current rule

Only synthetic and dry-run audit metadata belongs in this repo. Production conversation text, sealed transcripts, real firm records, credentials, secrets, and tokens do not belong here.

## Runtime audit envelope

Future synthetic audit envelopes should be able to carry:

- `audit_event_id`
- `runtime_route`
- `mode`
- `contract_repo_sha`
- `schema_version`
- `content_input_hash`
- `content_output_hash`
- `policy_decision`
- `tool_call_refs`
- `event_store_ref`
- `retention_class`
- `legal_hold_status`
- `audit_event_hash`
- `previous_audit_event_hash`

## Policy gates

Runtime work must fail closed when:

- the selected route lacks an audit expectation
- the contract SHA is ambiguous
- audit persistence behavior is unclear
- the task would store production conversation content
- the task would bypass Law Firm OS Semantic Substrate contract authority

## Authority

The Law Firm OS Semantic Substrate contract repository owns canonical audit contracts. This runtime may consume those contracts after they are published and pinned.
