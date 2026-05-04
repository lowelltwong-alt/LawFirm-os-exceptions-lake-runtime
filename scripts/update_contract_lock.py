from __future__ import annotations

import json
import sys
import subprocess
from datetime import UTC, datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from exceptions_lake_runtime.config import RuntimeConfig, RuntimeConfigError

LOCK_PATH = REPO_ROOT / "contracts.lock.json"


def resolve_contract_sha(contract_repo_root: Path) -> str:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=contract_repo_root,
            capture_output=True,
            text=True,
            check=True,
        )
    except (OSError, subprocess.CalledProcessError) as exc:
        raise RuntimeConfigError(
            "EXCEPTIONS_LAKE_CONTRACT_REPO_PATH must point to a git repository. "
            "Confirm the path is a valid repo with a readable HEAD commit."
        ) from exc
    return result.stdout.strip()


def build_lock_document(
    contract_sha: str, generated_at: str | None = None
) -> dict[str, object]:
    timestamp = generated_at or datetime.now(tz=UTC).isoformat().replace("+00:00", "Z")
    return {
        "contract_repo": "your-org/law-firm-ontology",
        "contract_ref_type": "git_sha",
        "contract_sha": contract_sha,
        "generated_at": timestamp,
        "generated_by": "exceptions-lake-runtime",
        "non_claims": [
            "no production runtime",
            "no real events",
            "no real connectors",
            "no dashboards",
            "no canon mutation",
        ],
    }


def main() -> int:
    config = RuntimeConfig.from_env()
    contract_sha = resolve_contract_sha(config.contract_repo_root)
    lock_document = build_lock_document(contract_sha)
    LOCK_PATH.write_text(
        json.dumps(lock_document, indent=2, sort_keys=False) + "\n",
        encoding="utf-8",
    )
    print(f"Updated contracts.lock.json to {contract_sha}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
