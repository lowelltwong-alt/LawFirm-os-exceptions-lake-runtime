# Runtime Stop Conditions

AI-assisted work in this runtime repo must stop and report when any condition below occurs.

## Contract authority

- Law Firm contract SHA is missing, ambiguous, or mismatched.
- Runtime code would redefine schema meaning, lifecycle states, mutation authority, or promotion authority.
- Law Firm contract drift would need to be bypassed instead of surfaced.

## Data and persistence

- The task requires real client, matter, employee, policy, incident, or operational data for the firm.
- The task would persist non-synthetic events outside approved dry-run behavior.
- The task would store raw production conversation content, sealed transcripts, credentials, secrets, or tokens in this repo.

## Runtime scope

- The task would add live connectors, dashboards, HTTP services, cloud deployment, production telemetry, or production audit lake behavior without explicit approval.
- The task would create adaptation proposals or promotion decisions automatically from runtime observations.

## Validation

- `pytest` fails and the fix is not clearly within the selected route.
- A failure would need to be converted into a silent skip.
- The contributor cannot state exact validation commands and results.
