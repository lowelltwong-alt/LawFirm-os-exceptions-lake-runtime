# Skill Quality Events

Exception Lake may store evidence about skill quality and skill failures. These are evidence-plane records, not approval authority.

Allowed event types:

- `skill_security_scan.failed`
- `skill_security_scan.passed`
- `skill_algorithm_grade.failed`
- `skill_algorithm_grade.passed`
- `skill_quality_review.failed`
- `skill_quality_review.passed`
- `skill_invocation.failed`
- `skill_gap_candidate.created`

No event in this list may approve a skill or mutate the Semantic Substrate.
