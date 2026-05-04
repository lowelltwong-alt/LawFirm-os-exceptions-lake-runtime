from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .config import RuntimeConfig

EXPORT_MANIFEST_RELATIVE_PATH = Path("registry/exceptions-lake-contract-export.json")
CONTRACT_LOCK_RELATIVE_PATH = Path("contracts.lock.json")

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
            required_schema_keys = list(
                dict.fromkeys(
                    export_manifest.get("canonical_schema_keys", []) + required_schema_keys
                )
            )
            manifest_docs = [
                Path(doc_path) for doc_path in export_manifest.get("required_docs", [])
            ]
            required_doc_paths = list(
                dict.fromkeys(manifest_docs + required_doc_paths)
            )

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

        contract_version = self._resolve_git_sha(contract_repo_root)
        locked_contract_sha = None
        if contract_lock is not None:
            locked_contract_sha = self._resolve_locked_contract_sha(contract_lock)
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
    def _resolve_locked_contract_sha(contract_lock: dict[str, Any]) -> str:
        locked_sha = contract_lock.get("contract_sha")
        if not isinstance(locked_sha, str) or not locked_sha:
            raise ContractLoadError(
                "contracts.lock.json is present but contract_sha is missing or invalid."
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
                "Unable to resolve contract_version from the contract repo git SHA."
            ) from exc
        return result.stdout.strip()
