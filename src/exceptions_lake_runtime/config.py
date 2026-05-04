from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

CONTRACT_REPO_ENV_VAR = "EXCEPTIONS_LAKE_CONTRACT_REPO_PATH"


class RuntimeConfigError(RuntimeError):
    """Raised when runtime configuration is invalid or unsafe."""


def _is_within(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
        return True
    except ValueError:
        return False


@dataclass(frozen=True)
class RuntimeConfig:
    contract_repo_root: Path
    runtime_data_dir: Path
    event_store_path: Path
    audit_log_path: Path
    contract_repo_env_var: str = CONTRACT_REPO_ENV_VAR

    @classmethod
    def from_env(cls, runtime_data_dir: str | Path | None = None) -> "RuntimeConfig":
        contract_repo_value = os.getenv(CONTRACT_REPO_ENV_VAR)
        if not contract_repo_value:
            raise RuntimeConfigError(
                f"{CONTRACT_REPO_ENV_VAR} must be set to a local contract repo path."
            )

        contract_repo_root = Path(contract_repo_value).expanduser().resolve()
        if not contract_repo_root.exists() or not contract_repo_root.is_dir():
            raise RuntimeConfigError(
                f"{CONTRACT_REPO_ENV_VAR} points to a missing or invalid directory: "
                f"{contract_repo_root}"
            )

        if runtime_data_dir is None:
            resolved_runtime_data_dir = (Path.cwd() / "runtime_data").resolve()
        else:
            resolved_runtime_data_dir = Path(runtime_data_dir).expanduser().resolve()

        if _is_within(resolved_runtime_data_dir, contract_repo_root):
            raise RuntimeConfigError(
                "runtime_data must not be nested inside the contract repo root."
            )

        return cls(
            contract_repo_root=contract_repo_root,
            runtime_data_dir=resolved_runtime_data_dir,
            event_store_path=resolved_runtime_data_dir / "events.jsonl",
            audit_log_path=resolved_runtime_data_dir / "audit.jsonl",
        )
