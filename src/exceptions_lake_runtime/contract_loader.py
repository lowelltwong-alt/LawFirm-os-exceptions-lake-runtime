from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .config import RuntimeConfig

EXPORT_MANIFEST_RELATIVE_PATH = Path("registry/exceptions-lake-contract-export.json")
CONTRACT_LOCK_RELATIVE_PATH = Path("contracts.lock.json")
REQUIRED_CONTRACT_LOCK_FIELDS = (
    "contract_repo",
    "contract_ref_type",
    "contract_sha",
    "generated_at",
    "generated_by",
)

REQUIRED_REGISTRY_RELATIVE_PATHS = (
    Path("registry/schema-registry.json"),
    Path("registry/exceptions-schema-registry.json"),
    Path("registry/governed-learning-schema-registry.json"),
    Path("registry/exception-route-registry.json"),
)

FALLBACK_REQUIRED_SCHEMA_KEYS = (
    "exception-event-v1",
    "pressure-vector-v1",
    "adaptation-proposal-v1",
    "promotion-decision-v1",
    "source-ingestion-manifest-schema-v1",
    "access-decision-schema-v1",
)

FALLBACK_REQUIRED_DOC_RELATIVE_PATHS = (
    Path("governance/EXCEPTIONS_LAKE_BOUNDARY.md"),
    Path("governance/AI_CONTROL_PLANE_BOUNDARY.md"),
)


class ContractLoadError(RuntimeError):
    """Raised when required contract surfaces cannot be loaded."""


@dataclass(frozen=True)
class ContractBundle:
    contract_repo_root: Path
    contract_version: str
    locked_contract_sha: str | None
    schema_paths: dict[str, Path]
    route_registry: dict[str, Any]
    boundary_doc_paths: dict[str, Path]
    export_manifest_present: bool
    export_manifest: dict[str, Any] | None
    contract_lock_path: Path | None


class ContractLoader:
    """Load versioned contract surfaces from the authoritative contract repo."""

    def load(self, config: RuntimeConfig) -> ContractBundle:
        contract_repo_root = config.contract_repo_root
        runtime_repo_root = Path(__file__).resolve().parents[2]

        registry_paths = {
            relative_path.name: self._require_path(contract_repo_root, relative_path)
            for relative_path in REQUIRED_REGISTRY_RELATIVE_PATHS
        }

        contract_lock_path = runtime_repo_root / CONTRACT_LOCK_RELATIVE_PATH
        contract_lock = (
            self._read_json(contract_lock_path) if contract_lock_path.exists() else None
        )
        contract_version = self._resolve_git_sha(contract_repo_root)

        export_manifest_path = contract_repo_root / EXPORT_MANIFEST_RELATIVE_PATH
        export_manifest_present = export_manifest_path.exists()
        export_manifest = (
            self._read_json(export_manifest_path) if export_manifest_present else None
        )

        schema_registries = [
            self._read_json(registry_paths["exceptions-schema-registry.json"]),
            self._read_json(registry_paths["governed-learning-schema-registry.json"]),
            self._read_json(registry_paths["schema-registry.json"]),
        ]
        route_registry = self._read_json(registry_paths["exception-route-registry.json"])

        registry_entries = self._build_registry_index(schema_registries)

        required_schema_keys = list(FALLBACK_REQUIRED_SCHEMA_KEYS)
        required_doc_paths = list(FALLBACK_REQUIRED_DOC_RELATIVE_PATHS)

        if export_manifest_present and export_manifest is not None:
            manifest_schema_keys = self._validate_manifest_schema_keys(export_manifest)
            manifest_docs = self._validate_manifest_required_docs(export_manifest)
            required_schema_keys = list(
                dict.fromkeys(manifest_schema_keys + required_schema_keys)
            )
            required_doc_paths = list(dict.fromkeys(manifest_docs + required_doc_paths))

        schema_paths: dict[str, Path] = {}
        for schema_key in required_schema_keys:
            entry = registry_entries.get(schema_key)
            if entry is None:
                raise ContractLoadError(f"Missing schema registry entry for {schema_key}.")

            relative_schema_path = entry.get("path")
            if not isinstance(relative_schema_path, str) or not relative_schema_path:
                raise ContractLoadError(
                    f"Schema entry for {schema_key} does not contain a valid path."
                )

            schema_paths[schema_key] = self._require_path(
                contract_repo_root, Path(relative_schema_path)
            )

        boundary_doc_paths: dict[str, Path] = {}
        for relative_doc_path in required_doc_paths:
            resolved_path = self._require_path(contract_repo_root, relative_doc_path)
            if relative_doc_path.name == "EXCEPTIONS_LAKE_BOUNDARY.md":
                boundary_doc_paths["exceptions_lake_boundary"] = resolved_path
            elif relative_doc_path.name == "AI_CONTROL_PLANE_BOUNDARY.md":
                boundary_doc_paths["ai_control_plane_boundary"] = resolved_path

        locked_contract_sha = None
        if contract_lock is not None:
            locked_contract_sha = self._validate_and_resolve_locked_contract_sha(
                contract_lock
            )
            if contract_version != locked_contract_sha:
                raise ContractLoadError(
                    "Live contract repo SHA does not match contracts.lock.json. "
                    "Run scripts/update_contract_lock.py to refresh the pin."
                )

        return ContractBundle(
            contract_repo_root=contract_repo_root,
            contract_version=contract_version,
            locked_contract_sha=locked_contract_sha,
            schema_paths=schema_paths,
            route_registry=route_registry,
            boundary_doc_paths=boundary_doc_paths,
            export_manifest_present=export_manifest_present,
            export_manifest=export_manifest,
            contract_lock_path=contract_lock_path if contract_lock is not None else None,
        )

    @staticmethod
    def _read_json(path: Path) -> dict[str, Any]:
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except FileNotFoundError as exc:
            raise ContractLoadError(f"Required JSON file is missing: {path}") from exc
        except json.JSONDecodeError as exc:
            raise ContractLoadError(f"Invalid JSON in {path}: {exc}") from exc

    @staticmethod
    def _require_path(contract_repo_root: Path, relative_path: Path) -> Path:
        resolved_path = (contract_repo_root / relative_path).resolve()
        if not resolved_path.exists():
            raise ContractLoadError(
                f"Required contract path is missing: {relative_path.as_posix()}"
            )
        return resolved_path

    @staticmethod
    def _validate_and_resolve_locked_contract_sha(contract_lock: dict[str, Any]) -> str:
        if not isinstance(contract_lock, dict):
            raise ContractLoadError(
                "contracts.lock.json is invalid: expected a JSON object. "
                "Run scripts/update_contract_lock.py to regenerate the lock file."
            )

        missing_fields = [
            field for field in REQUIRED_CONTRACT_LOCK_FIELDS if field not in contract_lock
        ]
        if missing_fields:
            missing = ", ".join(missing_fields)
            raise ContractLoadError(
                "contracts.lock.json is missing required field(s): "
                f"{missing}. Run scripts/update_contract_lock.py to regenerate the lock file."
            )

        contract_repo = contract_lock.get("contract_repo")
        if not isinstance(contract_repo, str) or not contract_repo.strip():
            raise ContractLoadError(
                "contracts.lock.json field 'contract_repo' is missing or invalid. "
                "Run scripts/update_contract_lock.py to regenerate the lock file."
            )

        contract_ref_type = contract_lock.get("contract_ref_type")
        if contract_ref_type != "git_sha":
            raise ContractLoadError(
                "contracts.lock.json field 'contract_ref_type' is invalid. "
                "Expected 'git_sha'. Run scripts/update_contract_lock.py to regenerate the lock file."
            )

        generated_at = contract_lock.get("generated_at")
        if not isinstance(generated_at, str) or not generated_at.strip():
            raise ContractLoadError(
                "contracts.lock.json field 'generated_at' is missing or invalid. "
                "Run scripts/update_contract_lock.py to regenerate the lock file."
            )

        generated_by = contract_lock.get("generated_by")
        if not isinstance(generated_by, str) or not generated_by.strip():
            raise ContractLoadError(
                "contracts.lock.json field 'generated_by' is missing or invalid. "
                "Run scripts/update_contract_lock.py to regenerate the lock file."
            )

        locked_sha = contract_lock.get("contract_sha")
        if not isinstance(locked_sha, str) or not locked_sha.strip():
            raise ContractLoadError(
                "contracts.lock.json field 'contract_sha' is missing or invalid. "
                "Run scripts/update_contract_lock.py to regenerate the lock file."
            )
        return locked_sha

    @staticmethod
    def _build_registry_index(
        schema_registries: list[dict[str, Any]]
    ) -> dict[str, dict[str, Any]]:
        indexed: dict[str, dict[str, Any]] = {}
        for registry in schema_registries:
            for entry in registry.get("schemas", []):
                schema_id = entry.get("schema_id")
                if isinstance(schema_id, str) and schema_id and schema_id not in indexed:
                    indexed[schema_id] = entry
        return indexed

    @staticmethod
    def _validate_manifest_schema_keys(export_manifest: dict[str, Any]) -> list[str]:
        schema_keys = export_manifest.get("canonical_schema_keys")
        if schema_keys is None:
            raise ContractLoadError(
                "Invalid export manifest field 'canonical_schema_keys': field is required."
            )
        if not isinstance(schema_keys, list):
            raise ContractLoadError(
                "Invalid export manifest field 'canonical_schema_keys': expected a list of schema IDs."
            )
        if not schema_keys:
            raise ContractLoadError(
                "Invalid export manifest field 'canonical_schema_keys': list must not be empty."
            )

        validated: list[str] = []
        for idx, schema_key in enumerate(schema_keys):
            if not isinstance(schema_key, str) or not schema_key.strip():
                raise ContractLoadError(
                    "Invalid export manifest field "
                    f"'canonical_schema_keys[{idx}]': expected a non-empty string schema ID."
                )
            validated.append(schema_key)
        return validated

    @staticmethod
    def _validate_manifest_required_docs(export_manifest: dict[str, Any]) -> list[Path]:
        required_docs = export_manifest.get("required_docs")
        if required_docs is None:
            raise ContractLoadError(
                "Invalid export manifest field 'required_docs': field is required."
            )
        if not isinstance(required_docs, list):
            raise ContractLoadError(
                "Invalid export manifest field 'required_docs': expected a list of relative contract paths."
            )
        if not required_docs:
            raise ContractLoadError(
                "Invalid export manifest field 'required_docs': list must not be empty."
            )

        validated: list[Path] = []
        for idx, doc_path in enumerate(required_docs):
            if not isinstance(doc_path, str) or not doc_path.strip():
                raise ContractLoadError(
                    "Invalid export manifest field "
                    f"'required_docs[{idx}]': expected a non-empty relative path string."
                )
            validated.append(Path(doc_path))
        return validated

    @staticmethod
    def _resolve_git_sha(contract_repo_root: Path) -> str:
        try:
            result = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                cwd=contract_repo_root,
                capture_output=True,
                text=True,
                check=True,
            )
        except (OSError, subprocess.CalledProcessError) as exc:
            raise ContractLoadError(
                "Unable to resolve contract_version from the contract repo git SHA. "
                "EXCEPTIONS_LAKE_CONTRACT_REPO_PATH must point to an actual git "
                "checkout of LawFirm-os-semantic-substrate at the pinned commit. "
                "A plain ZIP/archive extraction without .git metadata is not a "
                "verifiable contract source for runtime execution."
            ) from exc
        return result.stdout.strip()
