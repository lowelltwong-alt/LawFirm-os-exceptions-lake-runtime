from __future__ import annotations

import copy

TEMPLATE_TITLE = "BUDGET FORM"
INSTRUCTION_NOTE = (
    "Attorneys are only responsible for filling out the Original Budgeted Amount "
    "for initial budgets or New Budgeted Amount for supplemental budgets in "
    "this synthetic runtime draft."
)
TEMPLATE_FOOTER_NOTE = (
    "The accepted by carrier amounts are only accurate as of the date viewed "
    "in the ebilling portal in the sanitized template. This runtime emits "
    "synthetic placeholder amounts only."
)
BUDGET_COLUMNS = [
    "Original Budgeted Amount",
    "Amount Billed to Date",
    "Original Budget Amount Remaining",
    "New Budgeted Amount",
]
SUMMARY_LABELS = {
    "original_budget_label": "Original Budget:",
    "updated_budget_label": "Updated budget:",
}
ZERO_ROW_NOTE = "Synthetic placeholder row retained to mirror sanitized template shape."

TEMPLATE_PHASE_SECTIONS = [
    {
        "phase_code": "L100",
        "phase_label": "Case Assessment, Development and Administration",
        "rows": [
            ("L110", "Fact Investigation / Development"),
            ("L120", "Analysis / Strategy"),
            ("L130", "Experts / Consultants"),
            ("L140", "Document / File Management"),
            ("L150", "Budgeting"),
            ("L160", "Settlement / Non-Binding ADR"),
            ("L190", "Other Case Assessment, Development and Administration"),
        ],
    },
    {
        "phase_code": "L200",
        "phase_label": "Pre-Trial Pleading and Motions",
        "rows": [
            ("L210", "Pleading"),
            ("L220", "Preliminary Injunctions / Provisional Remedies"),
            ("L230", "Court Mandated Conferences"),
            ("L240", "Dispositive Motions"),
            ("L250", "Other Written Motions and Sanctions"),
            ("L260", "Class Action Certification and Notice"),
        ],
    },
    {
        "phase_code": "L300",
        "phase_label": "Discovery",
        "rows": [
            ("L310", "Written Discovery"),
            ("L320", "Document Production"),
            ("L330", "Depositions"),
            ("L340", "Expert Discovery"),
            ("L350", "Discovery Motions"),
            ("L390", "Other Discovery"),
        ],
    },
    {
        "phase_code": "L400",
        "phase_label": "Trial Preparation and Trial",
        "rows": [
            ("L410", "Fact Witnesses"),
            ("L420", "Expert Witnesses"),
            ("L430", "Written Motions and Submissions"),
            ("L440", "Other Trial Preparation and Support"),
            ("L450", "Trial and Hearing Attendance"),
            ("L460", "Post-Trial Motions and Submissions"),
            ("L470", "Enforcement"),
        ],
    },
    {
        "phase_code": "L500",
        "phase_label": "Appeal",
        "rows": [
            ("L510", "Appellate Motions and Submissions"),
            ("L520", "Appellate Briefs"),
            ("L530", "Oral Argument"),
        ],
    },
    {
        "phase_code": "E100",
        "phase_label": "Expenses",
        "rows": [
            ("E101", "Copying"),
            ("E102", "Outside Printing"),
            ("E103", "Word Processing"),
            ("E104", "Facsimile"),
            ("E105", "Telephone"),
            ("E106", "Online Research"),
            ("E107", "Messengers / Overnite"),
            ("E108", "Postage"),
            ("E109", "Local Travel"),
            ("E110", "Out-of-Town Travel"),
            ("E111", "Meals"),
            ("E112", "Court Fees"),
            ("E113", "Subpoena Fees"),
            ("E114", "Witness Fees"),
            ("E115", "Court Reporting & Transcripts"),
            ("E116", "Trial Transcripts"),
            ("E117", "Trial Exhibits"),
            ("E118", "Litigation, Support Vendors"),
            ("E119", "Experts"),
            ("E120", "Private Investigators"),
            ("E121", "Arbitrators / Mediators"),
            ("E122", "Local Counsel"),
            ("E123", "Other Professionals"),
            ("E124", "Other"),
        ],
    },
]

PHASE_CODE_TO_ROW_CODES = {
    phase["phase_code"]: [row_code for row_code, _ in phase["rows"]]
    for phase in TEMPLATE_PHASE_SECTIONS
}
ROW_CODE_TO_LABEL = {
    row_code: row_label
    for phase in TEMPLATE_PHASE_SECTIONS
    for row_code, row_label in phase["rows"]
}
ROW_CODE_TO_PHASE_CODE = {
    row_code: phase["phase_code"]
    for phase in TEMPLATE_PHASE_SECTIONS
    for row_code, _ in phase["rows"]
}


def build_template_phase_sections() -> list[dict[str, object]]:
    return copy.deepcopy(TEMPLATE_PHASE_SECTIONS)


def ordered_phase_codes() -> list[str]:
    return [phase["phase_code"] for phase in TEMPLATE_PHASE_SECTIONS]


def ordered_row_codes() -> list[str]:
    return [row_code for phase in TEMPLATE_PHASE_SECTIONS for row_code, _ in phase["rows"]]


def expand_emphasis_refs(refs: list[str]) -> list[str]:
    expanded: list[str] = []
    for ref in refs:
        if ref in PHASE_CODE_TO_ROW_CODES:
            expanded.extend(PHASE_CODE_TO_ROW_CODES[ref])
        elif ref in ROW_CODE_TO_LABEL:
            expanded.append(ref)
    return list(dict.fromkeys(expanded))
