# Legal Knowledge Research Delta Events

This document defines event families that may be represented in Exception Lake only as metadata, traces, defects, receipts, and evidence references.

## Allowed event families

- `legal_retrieval_eval_completed`
- `legal_document_integrity_check_completed`
- `legal_agent_safety_check_completed`
- `legal_context_bundle_guardrail_triggered`
- `legal_claim_verification_failed`

## Forbidden payloads

Do not store:

- full legal documents;
- full matter files;
- raw privileged payloads;
- secrets or tokens;
- chain-of-thought or hidden reasoning;
- unrestricted prompt transcripts.

Use claim-check refs, hashes, schema IDs, trace IDs, and result summaries.
