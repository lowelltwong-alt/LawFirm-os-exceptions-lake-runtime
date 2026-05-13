# Workflow Atlas Signal Policy

Workflow Atlas signals are evidence candidates and capture-gap indicators.

They should enter the Exception Lake only through supported validation boundaries and only as append-only evidence or audit records.

They must not create canonical route IDs, event classes, schema changes, ontology updates, or promotion decisions.

## Accepted seed route

- `route.workflow_escalation.v1`
- `workflow_escalation`

## Common signal types

- `workflow_atlas_capture_gap`
- `manual_process_outside_lake`
- `same_job_intake_disagreement`
- `technology_workflow_detail_missing`
- `visual_correction_needed`
- `musk_algorithm_deletion_candidate`

## Raw transcript boundary

Do not store raw Teams transcripts, raw voice transcripts, privileged content, or sealed transcript text in the Exception Lake.

Store hashes, references, redaction status, workflow fragment IDs, correction event IDs, integrity report IDs, and evidence packet IDs.

## Pressure vector path

Workflow Atlas signal → reviewed evidence packet → aggregate pattern → pressure vector candidate → governance proposal package → human review → promotion decision if needed.
