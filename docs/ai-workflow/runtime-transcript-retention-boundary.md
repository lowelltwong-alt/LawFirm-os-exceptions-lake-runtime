# Runtime Transcript Retention Boundary

This runtime repo must not store production conversation text or sealed transcript contents.

## Boundary

Allowed in this repo:

- synthetic examples
- dry-run metadata
- content hashes
- audit envelope metadata
- pointers documented as examples only
- retention-class documentation

Not allowed in this repo:

- production conversation text
- sealed transcript contents
- real FMG records
- privileged matter content
- credentials, secrets, or tokens
- production audit lake storage

## Future production pattern

If production AI interaction audit capture is approved later, the runtime should write only approved audit envelopes and storage pointers. Sealed transcript content must be stored in an external secure store with:

- encryption
- access controls
- retention schedule
- legal-hold workflow
- privilege/confidentiality review
- audit access logging

## Default retention posture

Synthetic and dry-run artifacts may use short retention. Production retention classes must be defined by FMG governance before production capture is enabled.
