---
artifact: true
artifact_type: technical_crosswalk
status: proposed
canon_status: not_canon_until_approved
authority: explanatory_only
review_cycle: 6 months
stale_after: 2026-11-29
---

# Shannon Error Correction and Exception Lake

Status: Non-canonical concept note.
Authority: Explanatory only. Does not modify persistence, event schemas, contract pins, audit behavior, or any canonical authority.

## BLUF

The Exception Lake Runtime is, structurally, an error-detection and error-correction system over a noisy runtime channel. Exception events are observations. Pressure vectors are compressed summaries of repeated or high-information observations. Adaptation proposals and promotion decisions are governance paths. No runtime observation directly mutates canon. Shannon information theory makes that role precise; it does not authorize new mutations of any kind.

Conceptual lineage: this note draws on Shannon (1948), Cover & Thomas (*Elements of Information Theory*), and MacKay (*Information Theory, Inference, and Learning Algorithms*); see the **References** section. No file outside this repository is required to read this note.

## Boundary

This note does **not**:

- modify any persistence (append-only JSONL event store, audit log);
- modify event schemas, route registry behavior, or `contracts.lock.json`;
- alter the deny-by-default policy gate or the synthetic-only MVP boundary;
- imply that runtime evidence directly mutates substrate canon;
- create new event classes, pressure-vector types, or promotion paths.

The substrate's governed path remains:

```text
exception-event -> pressure-vector -> adaptation-proposal -> promotion-decision
```

## Communication model

| Shannon layer | Exception Lake-local equivalent |
|---|---|
| Information source | Real or synthetic operating reality the runtime is observing (what actually happened, what was expected, where the policy gate fired) |
| Transmitter | The orchestrator or operator producing an `exception-event` candidate payload |
| Channel | Contract validation → route registry check → deny-by-default policy gate → append-only event store |
| Noise | Mis-classified event, omitted route, unpinned contract clone, missing metadata, audit-log gap, synthetic-vs-real confusion |
| Receiver | The append-only event store + audit log + in-memory pressure-vector candidate builder |
| Destination | Future readiness preflight, downstream governance review, eventual proposal/decision |
| Redundancy | `contracts.lock.json`, route registry pin, JSON-Schema validation, append-only audit log, dual event-and-audit records |
| Error correction | Pressure-vector candidate aggregation (compresses repeated events), governed proposal/decision path (corrects substrate when warranted) |
| Channel capacity | Event-store throughput, reviewer bandwidth, validator coverage, the substrate's promotion-decision throughput |

## Real math used

Notation:

- $E$ = exception event drawn from the runtime distribution over event classes.
- $P_t$ = empirical exception distribution over a window ending at time $t$.
- $P_0$ = baseline exception distribution (an explicit, governed reference window).
- $X$ = the canonical fact the runtime is implicitly trying to surface (e.g., "this route's policy must change").
- $Y$ = the observed exception candidate after contract+route validation.
- $\hat{X}$ = the pressure-vector candidate's implicit classification of $X$.

### Self-information of a rare event

```math
I(e) \;=\; -\log_2 p(e)
```

Lake interpretation:

- A rare exception class carries more information per occurrence than a common one. The lake should not weight purely by frequency: low-frequency, high-surprise events can reveal a governance gap. This is **not** a license to mutate canon. It is a reason to surface the event for review.

### Entropy of the current exception mix

```math
H(E) \;=\; -\sum_{e} p(e)\,\log_2 p(e)
```

Lake interpretation:

- High $H(E)$ over a window indicates broad, scattered exception behavior — many small failure modes. Low $H(E)$ with mass concentrated on one class indicates a dominant failure mode. Both are signals to a human reviewer; neither alone is a promotion trigger.

### Drift via KL divergence (optional, data-dependent)

```math
D_{\mathrm{KL}}(P_t \,\Vert\, P_0) \;=\; \sum_{e} P_t(e)\,\log_2 \frac{P_t(e)}{P_0(e)}
```

Lake interpretation:

- *If* a baseline window $P_0$ is governed and published (it currently is not), $D_{\mathrm{KL}}$ would be the canonical drift metric. **Today this is conceptual; the MVP is synthetic-first.** Any future drift gauge must:
  - declare $P_0$ explicitly,
  - smooth zero-count classes to avoid infinite values,
  - report a confidence interval, and
  - go through the governed promotion path rather than auto-trigger any change.

### Data processing inequality

For $X \to Y \to \hat{X}$:

```math
I(X; \hat{X}) \;\le\; I(X;Y)
```

Lake interpretation (the structural rule):

- A pressure-vector candidate $\hat{X}$ cannot carry more information about the canonical fact $X$ than the validated exception candidate $Y$ already carried. **Pressure aggregation compresses; it does not create new authority.** This is the substrate's mutation boundary expressed as a coding bound.

### Fano-style sanity check for high-stakes classifications

If a class set $\mathcal{X}$ is well defined and a classifier $\hat{X}$ is in use, then for error probability $P_e$:

```math
H(X \mid \hat{X}) \;\le\; h_2(P_e) \;+\; P_e \log_2(|\mathcal{X}| - 1)
```

A useful one-line consequence: if residual classification uncertainty $H(X \mid \hat{X})$ stays high, $P_e$ cannot be small. **Design rule:** do not let fluent rationale hide unavoidable error probability. Where stakes are high, prefer human review to confident text.

### Hamming-style redundancy

For a block code with minimum Hamming distance $d_{\min}$:

```math
\text{detectable errors} = d_{\min} - 1, \qquad \text{correctable errors} = \left\lfloor \frac{d_{\min}-1}{2} \right\rfloor
```

Lake interpretation:

- The dual record (event store + audit log) is a minimal redundancy that detects single-record corruption. `contracts.lock.json` is a checksum that detects unpinned-clone drift. Neither claims correction; both enable detection. The governed proposal/decision path is the correction layer.

## Integration implications

These are conceptual implications, not new requirements:

1. **Exceptions are evidence, not canon.** The data processing inequality formalizes why: nothing in the Markov chain downstream of the validated event can carry more canonical information than the substrate channel preserved.
2. **Pressure vectors are compression, not promotion.** They reduce $H(E)$ by collapsing repeated low-information events into a higher-information summary. Compression cannot create authority — that is the data processing inequality again.
3. **Drift detection requires governed baselines.** Without a published $P_0$, $D_{\mathrm{KL}}$ has no meaning. The current MVP does not have one. Any future drift gauge must be proposed through the substrate's promotion-decision path.
4. **Rare-event weighting must be transparent.** If self-information is used to prioritize review, the weighting function must be documented and reviewable. Hidden weighting is opaque to governance.
5. **Synthetic-vs-real labels must persist.** A synthetic-only event must never be confused with a real-runtime event in any downstream summary. The compression layer must preserve this label or it has injected noise.

## Safe design questions

For each candidate event/pressure aggregation path:

1. What is the authoritative source for this event class (substrate registry entry, governed route)?
2. How is the event encoded so a reviewer can reconstruct the canonical fact (JSON-Schema, route registry, audit log)?
3. Where can channel noise enter (mis-routed event, unpinned clone, missing metadata, synthetic/real mix-up)?
4. Is the lake's aggregation surface still inside reviewer/validator capacity?
5. What redundancy detects regressions (dual records, contract-lock checks, registry validation)?
6. What governed error-correction path applies (proposal → decision), and who decides promotion?
7. If the pressure vector implicitly classifies, what is the class set and what residual uncertainty remains?

## Non-goals

- This note does not introduce $D_{\mathrm{KL}}$, $H(E)$, or self-information as required runtime metrics. The MVP is synthetic-first and contract-locked. Any new metric must be proposed through the governed path with explicit baseline data.
- This note does not authorize runtime mutation of substrate canon. Promotion remains governed.
- This note does not assert that Shannon math proves the lake's design. The lake's design comes from substrate governance, not from theorems.

## References

Conceptual only.

- Claude E. Shannon, "A Mathematical Theory of Communication," 1948.
- Thomas M. Cover and Joy A. Thomas, *Elements of Information Theory*, Wiley.
- David J. C. MacKay, *Information Theory, Inference, and Learning Algorithms*, Cambridge University Press.
