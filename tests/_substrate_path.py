from __future__ import annotations

import os
from pathlib import Path


def resolve_substrate_root(repo_root: Path) -> Path:
    """Resolve Semantic Substrate for tests in local and GitHub Actions layouts."""
    candidates: list[Path] = []
    for env_var in ("EXCEPTIONS_LAKE_CONTRACT_REPO_PATH", "LFOS_SUBSTRATE_PATH"):
        value = os.environ.get(env_var)
        if value:
            candidates.append(Path(value).expanduser())
    candidates.extend(
        [
            repo_root / "LawFirm-os-semantic-substrate",
            repo_root.parent / "LawFirm-os-semantic-substrate",
        ]
    )
    for candidate in candidates:
        registry = candidate / "registry" / "runtime-reason-codes-registry.json"
        if candidate.is_dir() and registry.is_file():
            return candidate.resolve()
    checked = ", ".join(str(path) for path in candidates)
    raise FileNotFoundError(f"Semantic Substrate runtime reason-code registry not found. Checked: {checked}")
