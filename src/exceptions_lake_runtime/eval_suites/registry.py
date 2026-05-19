"""Registry-backed eval suite mapping and canonical acceptance step templates."""
from __future__ import annotations

from exceptions_lake_runtime.substrate import reason_codes as rc


# Substrate eval-suite names (eval-candidate.schema.json description).
CANONICAL_EVAL_SUITES = frozenset(
    {
        rc.ROUTE_MISMATCH,
        rc.EVIDENCE_GAP,
        rc.UNSUPPORTED_CITATION,
        rc.PROMPT_INJECTION,
        rc.STALE_LAW,
        rc.APPROVAL_BYPASS,
        rc.DESTINATION_PRIVILEGE,
        rc.PASSPORT_DENIAL,
    }
)

# Map runtime defect classes that are not suite names to a canonical suite.
_DEFECT_TO_SUITE: dict[str, str] = {
    rc.HASH_MISMATCH: rc.EVIDENCE_GAP,
    rc.MISSING_PASSPORT: rc.PASSPORT_DENIAL,
    rc.DENIED_ACTION_RECORDED: rc.PASSPORT_DENIAL,
}


def eval_suite_for_defect_class(defect_class: str) -> str:
    if defect_class in CANONICAL_EVAL_SUITES:
        return defect_class
    if defect_class in _DEFECT_TO_SUITE:
        return _DEFECT_TO_SUITE[defect_class]
    raise ValueError(f"no eval suite mapping for defect class: {defect_class}")


def suite_step_templates(defect_class: str) -> list[tuple[str, str]]:
    """Return (step_id, plain-language description) templates for acceptance tests."""
    suite = eval_suite_for_defect_class(defect_class)
    common = [
        ("assert-proposal-only", "Assert eval candidate remains proposal-only (promotion_status=candidate)."),
        ("assert-no-substrate-mutation", "Assert the replay path does not mutate Semantic Substrate canon."),
    ]
    specific: dict[str, list[tuple[str, str]]] = {
        rc.ROUTE_MISMATCH: [
            ("replay-governed-route", "Replay execution under governed route map; expect denial or reroute."),
        ],
        rc.EVIDENCE_GAP: [
            ("replay-packet-integrity", "Replay evidence packet admission; expect reject or quarantine on gap."),
            ("assert-hash-chain", "Assert evidence packet hash chain fails closed on tamper."),
        ],
        rc.UNSUPPORTED_CITATION: [
            ("replay-claim-support", "Replay claim verification; unsupported claim must not promote to canon."),
        ],
        rc.PROMPT_INJECTION: [
            ("replay-retrieved-text", "Replay retrieved text handling; instruction-like content stays anomaly evidence."),
        ],
        rc.STALE_LAW: [
            ("replay-freshness-gate", "Replay freshness validation; stale bundled law flagged not executed."),
        ],
        rc.APPROVAL_BYPASS: [
            ("replay-write-approval", "Replay write action without approval; expect requires_approval or deny."),
        ],
        rc.DESTINATION_PRIVILEGE: [
            ("replay-destination-policy", "Replay external destination policy; expect deny for forbidden sink."),
        ],
        rc.PASSPORT_DENIAL: [
            ("replay-passport-gate", "Replay bounded action without passport; expect defect or deny."),
            ("replay-denied-action-evidence", "Replay denied action path; denial preserved as execution evidence."),
        ],
    }
    return list(specific.get(suite, [])) + common
