# Legal Knowledge Events

The Exception Lake may record legal knowledge runtime events as evidence, but it may not store full raw real-client document payloads or promote retrieval outputs into canonical meaning.

## Allowed event families

- `legal_knowledge.ingestion_preflight_blocked`
- `legal_knowledge.retrieval_trace_recorded`
- `legal_knowledge.context_bundle_built`
- `legal_knowledge.privilege_boundary_blocked`
- `legal_knowledge.retrieval_quality_defect`

## Required evidence

Every event should include:

- `run_id`
- `trace_id`
- `manifest_id`
- `retrieval_trace_id` when applicable
- `bundle_id` when applicable
- hashes and claim-check refs
- access policy ref
- redacted failure reasons

## Forbidden evidence

- full document text from real client/matter files;
- hidden chain-of-thought;
- secrets or credentials;
- production DMS credentials;
- unbounded tool payload dumps.
