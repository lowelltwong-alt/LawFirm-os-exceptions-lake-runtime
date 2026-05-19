"""PR-11 defect-to-eval minting entrypoint (proposal-only)."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from exceptions_lake_runtime.generators.eval_candidate_generator import (
    generate_eval_candidate_from_defect,
)
from exceptions_lake_runtime.governance.substrate_mutation_guard import (
    assert_substrate_unchanged,
    snapshot_substrate_governance_files,
)


def mint_eval_candidate(
    defect: dict[str, Any],
    *,
    packet: dict[str, Any] | None = None,
    generated_at: str | None = None,
    substrate_root: str | Path | None = None,
) -> dict[str, Any] | None:
    """Mint a proposal-only EvalCandidate from a DefectRecord.

    When ``substrate_root`` is provided, asserts minting does not mutate Substrate files.
    """
    before = None
    if substrate_root is not None:
        before = snapshot_substrate_governance_files(Path(substrate_root))

    candidate = generate_eval_candidate_from_defect(
        defect,
        packet=packet,
        generated_at=generated_at,
    )

    if substrate_root is not None and before is not None:
        assert_substrate_unchanged(before, Path(substrate_root))

    return candidate
