from __future__ import annotations

import fnmatch
import hashlib
import json
import sys
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from exceptions_lake_runtime.config import RuntimeConfig, RuntimeConfigError

LOCK_PATH = REPO_ROOT / "contracts.lock.json"
HASH_ALGORITHM = "lawfirm_os_contract_surface_sha256.v1"


def _matches(rel: str, pattern: str) -> bool:
    rel = rel.replace("\\", "/")
    pattern = pattern.replace("\\", "/")
    if fnmatch.fnmatch(rel, pattern):
        return True
    if pattern.endswith("/**"):
        return rel.startswith(pattern[:-3].rstrip("/") + "/")
    if pattern.endswith("/**/*"):
        return rel.startswith(pattern[:-5].rstrip("/") + "/")
    if "/**/" in pattern and fnmatch.fnmatch(rel, pattern.replace("/**/", "/")):
        return True
    return False


def _git_bytes(repo: Path, args: list[str]) -> bytes:
    try:
        return subprocess.run(["git", *args], cwd=repo, capture_output=True, check=True).stdout
    except (OSError, subprocess.CalledProcessError) as exc:
        raise RuntimeConfigError(
            "Unable to read the committed contract surface. "
            "EXCEPTIONS_LAKE_CONTRACT_REPO_PATH must point to a readable Semantic Substrate git checkout."
        ) from exc


def compute_committed_surface_result(contract_repo_root: Path, contract_sha: str, *, surface_id: str, registry_path: str) -> dict[str, Any]:
    registry = json.loads(_git_bytes(contract_repo_root, ["show", f"{contract_sha}:{registry_path}"]).decode("utf-8"))
    surface = None
    for candidate in registry.get("surfaces", []):
        if candidate.get("surface_id") == surface_id:
            surface = candidate
            break
    if surface is None:
        raise RuntimeConfigError(f"unknown contract surface id: {surface_id}")
    include_patterns = list(surface.get("include_patterns", []))
    exclude_patterns = list(surface.get("exclude_patterns", []))
    raw_paths = _git_bytes(contract_repo_root, ["ls-tree", "-r", "-z", "--name-only", contract_sha])
    items: list[dict[str, object]] = []
    for rel in sorted(path for path in raw_paths.decode("utf-8").split("\0") if path):
        if any(part in {".git", "__pycache__", ".pytest_cache", ".ruff_cache"} for part in Path(rel).parts):
            continue
        if not any(_matches(rel, pattern) for pattern in include_patterns):
            continue
        if any(_matches(rel, pattern) for pattern in exclude_patterns):
            continue
        data = _git_bytes(contract_repo_root, ["show", f"{contract_sha}:{rel}"])
        items.append({"path": rel, "sha256": hashlib.sha256(data).hexdigest(), "size_bytes": len(data)})
    if not items:
        raise RuntimeConfigError("contract surface selected zero files")
    manifest_bytes = json.dumps(items, sort_keys=True, separators=(",", ":")).encode("utf-8")
    digest = hashlib.sha256()
    digest.update(HASH_ALGORITHM.encode("utf-8"))
    digest.update(b"\0")
    digest.update(surface_id.encode("utf-8"))
    digest.update(b"\0")
    for item in items:
        digest.update(str(item["path"]).encode("utf-8"))
        digest.update(b"\0")
        digest.update(str(item["sha256"]).encode("ascii"))
        digest.update(b"\0")
        digest.update(str(item["size_bytes"]).encode("ascii"))
        digest.update(b"\0")
    return {
        "surface_sha256": digest.hexdigest(),
        "included_file_count": len(items),
        "included_files_manifest_sha256": hashlib.sha256(manifest_bytes).hexdigest(),
    }


def resolve_contract_sha(contract_repo_root: Path) -> str:
    try:
        result = subprocess.run(["git", "rev-parse", "HEAD"], cwd=contract_repo_root, capture_output=True, text=True, check=True)
    except (OSError, subprocess.CalledProcessError) as exc:
        raise RuntimeConfigError(
            "EXCEPTIONS_LAKE_CONTRACT_REPO_PATH must point to a git repository. Confirm the path is a valid repo with a readable HEAD commit."
        ) from exc
    return result.stdout.strip()


def compute_surface_lock(contract_repo_root: Path, contract_sha: str) -> dict[str, Any]:
    registry_path = "registry/contract-surface-registry.json"
    surface_id = "lawfirm_os_semantic_substrate.consumer_contract_surface.v1"
    surface = compute_committed_surface_result(
        contract_repo_root,
        contract_sha,
        surface_id=surface_id,
        registry_path=registry_path,
    )
    return {
        "surface_id": surface_id,
        "surface_sha256": surface["surface_sha256"],
        "surface_registry_path": registry_path,
        "hash_algorithm": HASH_ALGORITHM,
        "computed_from_repo": "LawFirm-os-semantic-substrate",
        "computed_from_commit": contract_sha,
        "included_file_count": surface["included_file_count"],
        "included_files_manifest_sha256": surface["included_files_manifest_sha256"],
        "notes": [
            "Consumer validates contract_surface_lock.surface_sha256 to avoid recursive drift from managed-patch decision/audit commits.",
            "contract_sha remains provenance for the Substrate commit used to compute this surface lock."
        ]
    }


def build_lock_document(contract_sha: str, generated_at: str | None = None, surface_lock: dict[str, Any] | None = None) -> dict[str, object]:
    timestamp = generated_at or datetime.now(tz=UTC).isoformat().replace("+00:00", "Z")
    document: dict[str, object] = {
        "contract_repo": "LawFirm-os-semantic-substrate",
        "contract_ref_type": "git_sha",
        "contract_sha": contract_sha,
        "substrate_repo_commit_sha": contract_sha,
        "generated_at": timestamp,
        "generated_by": "exceptions-lake-runtime-main",
        "contract_repo_human_label": "Law Firm OS Semantic Substrate",
        "pin_rationale": "Pinned by contract surface hash to avoid recursive drift from managed-patch decision/audit commits.",
        "manifest_first_loading": {
            "preferred_path": "registry/exceptions-lake-contract-export.json",
            "fallback_allowed_when_export_absent": True,
            "fallback_paths": [
                "registry/schema-registry.json",
                "registry/exceptions-schema-registry.json",
                "registry/governed-learning-schema-registry.json",
                "registry/exception-route-registry.json",
            ],
        },
        "non_claims": [
            "no production runtime",
            "no real events",
            "no real connectors",
            "no dashboards",
            "no canon mutation",
            "no promotion to canon",
            "no live model calls",
            "no scheduled jobs",
            "no live research crawling",
            "no external APIs",
            "no external writes",
            "no invented route_id or event_class",
        ],
    }
    if surface_lock is not None:
        document["contract_surface_lock"] = surface_lock
    return document


def main() -> int:
    config = RuntimeConfig.from_env()
    contract_sha = resolve_contract_sha(config.contract_repo_root)
    surface_lock = compute_surface_lock(config.contract_repo_root, contract_sha)
    lock_document = build_lock_document(contract_sha, surface_lock=surface_lock)
    LOCK_PATH.write_text(json.dumps(lock_document, indent=2, sort_keys=False) + "\n", encoding="utf-8")
    print(f"Updated contracts.lock.json to contract surface {surface_lock['surface_sha256']} from {contract_sha}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
