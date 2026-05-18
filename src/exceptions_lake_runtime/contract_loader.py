from __future__ import annotations

import fnmatch
import hashlib
import json
import re
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
HASH_ALGORITHM = "lawfirm_os_contract_surface_sha256.v1"

_LS_TREE_ENTRY_Z = re.compile(rb"^(\d+) (\w+) ([0-9a-f]{40})\t(.*)$")

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
    validated_ref_type: str | None = None
    validated_ref: str | None = None


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
        contract_lock = self._read_json(contract_lock_path) if contract_lock_path.exists() else None
        contract_version = self._resolve_git_sha(contract_repo_root)

        export_manifest_path = contract_repo_root / EXPORT_MANIFEST_RELATIVE_PATH
        export_manifest_present = export_manifest_path.exists()
        export_manifest = self._read_json(export_manifest_path) if export_manifest_present else None

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
            required_schema_keys = list(dict.fromkeys(manifest_schema_keys + required_schema_keys))
            required_doc_paths = list(dict.fromkeys(manifest_docs + required_doc_paths))

        schema_paths: dict[str, Path] = {}
        for schema_key in required_schema_keys:
            entry = registry_entries.get(schema_key)
            if entry is None:
                raise ContractLoadError(f"Missing schema registry entry for {schema_key}.")
            relative_schema_path = entry.get("path")
            if not isinstance(relative_schema_path, str) or not relative_schema_path:
                raise ContractLoadError(f"Schema entry for {schema_key} does not contain a valid path.")
            schema_paths[schema_key] = self._require_path(contract_repo_root, Path(relative_schema_path))

        boundary_doc_paths: dict[str, Path] = {}
        for relative_doc_path in required_doc_paths:
            resolved_path = self._require_path(contract_repo_root, relative_doc_path)
            if relative_doc_path.name == "EXCEPTIONS_LAKE_BOUNDARY.md":
                boundary_doc_paths["exceptions_lake_boundary"] = resolved_path
            elif relative_doc_path.name == "AI_CONTROL_PLANE_BOUNDARY.md":
                boundary_doc_paths["ai_control_plane_boundary"] = resolved_path

        locked_contract_sha = None
        validated_ref_type = None
        validated_ref = None
        if contract_lock is not None:
            locked_contract_sha = self._validate_and_resolve_locked_contract_sha(contract_lock)
            surface_lock = contract_lock.get("contract_surface_lock") if isinstance(contract_lock.get("contract_surface_lock"), dict) else None
            if surface_lock:
                validated_ref = self._validate_contract_surface_lock(contract_repo_root, surface_lock, contract_lock)
                validated_ref_type = "contract_surface_sha256"
            else:
                validated_ref_type = "git_sha"
                validated_ref = contract_version

        if locked_contract_sha is not None and contract_version != locked_contract_sha:
            raise ContractLoadError(
                "Live contract repo SHA does not match contracts.lock.json. Run scripts/update_contract_lock.py to refresh the pin."
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
            validated_ref_type=validated_ref_type,
            validated_ref=validated_ref,
        )

    @staticmethod
    def _read_json(path: Path) -> dict[str, Any]:
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except FileNotFoundError as exc:
            if "contract-surface-registry" in path.as_posix():
                raise ContractLoadError(
                    "Governed contract surface registry is missing under the contract repo. "
                    "Expected registry/contract-surface-registry.json (or the path declared in contract_surface_lock.surface_registry_path). "
                    "Restore Semantic Substrate from the pinned commit or refresh contracts.lock.json."
                ) from exc
            raise ContractLoadError(f"Required JSON file is missing: {path}") from exc
        except json.JSONDecodeError as exc:
            raise ContractLoadError(f"Invalid JSON in {path}: {exc}") from exc

    @staticmethod
    def _require_path(contract_repo_root: Path, relative_path: Path) -> Path:
        resolved_path = (contract_repo_root / relative_path).resolve()
        if not resolved_path.exists():
            raise ContractLoadError(f"Required contract path is missing: {relative_path.as_posix()}")
        return resolved_path

    @staticmethod
    def _validate_and_resolve_locked_contract_sha(contract_lock: dict[str, Any]) -> str:
        if not isinstance(contract_lock, dict):
            raise ContractLoadError("contracts.lock.json is invalid: expected a JSON object. Run scripts/update_contract_lock.py to regenerate the lock file.")
        missing_fields = [field for field in REQUIRED_CONTRACT_LOCK_FIELDS if field not in contract_lock]
        if missing_fields:
            missing = ", ".join(missing_fields)
            raise ContractLoadError(f"contracts.lock.json is missing required field(s): {missing}. Run scripts/update_contract_lock.py to regenerate the lock file.")
        contract_repo = contract_lock.get("contract_repo")
        if not isinstance(contract_repo, str) or not contract_repo.strip():
            raise ContractLoadError("contracts.lock.json field 'contract_repo' is missing or invalid. Run scripts/update_contract_lock.py to regenerate the lock file.")
        contract_ref_type = contract_lock.get("contract_ref_type")
        if contract_ref_type != "git_sha":
            raise ContractLoadError("contracts.lock.json field 'contract_ref_type' is invalid. Expected 'git_sha'. Run scripts/update_contract_lock.py to regenerate the lock file.")
        generated_at = contract_lock.get("generated_at")
        if not isinstance(generated_at, str) or not generated_at.strip():
            raise ContractLoadError("contracts.lock.json field 'generated_at' is missing or invalid. Run scripts/update_contract_lock.py to regenerate the lock file.")
        generated_by = contract_lock.get("generated_by")
        if not isinstance(generated_by, str) or not generated_by.strip():
            raise ContractLoadError("contracts.lock.json field 'generated_by' is missing or invalid. Run scripts/update_contract_lock.py to regenerate the lock file.")
        locked_sha = contract_lock.get("contract_sha")
        if not isinstance(locked_sha, str) or not locked_sha.strip():
            raise ContractLoadError("contracts.lock.json field 'contract_sha' is missing or invalid. Run scripts/update_contract_lock.py to regenerate the lock file.")
        return locked_sha

    @staticmethod
    def _build_registry_index(schema_registries: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
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
            raise ContractLoadError("Invalid export manifest field 'canonical_schema_keys': field is required.")
        if not isinstance(schema_keys, list):
            raise ContractLoadError("Invalid export manifest field 'canonical_schema_keys': expected a list of schema IDs.")
        if not schema_keys:
            raise ContractLoadError("Invalid export manifest field 'canonical_schema_keys': list must not be empty.")
        validated: list[str] = []
        for idx, schema_key in enumerate(schema_keys):
            if not isinstance(schema_key, str) or not schema_key.strip():
                raise ContractLoadError(f"Invalid export manifest field 'canonical_schema_keys[{idx}]': expected a non-empty string schema ID.")
            validated.append(schema_key)
        return validated

    @staticmethod
    def _validate_manifest_required_docs(export_manifest: dict[str, Any]) -> list[Path]:
        required_docs = export_manifest.get("required_docs")
        if required_docs is None:
            raise ContractLoadError("Invalid export manifest field 'required_docs': field is required.")
        if not isinstance(required_docs, list):
            raise ContractLoadError("Invalid export manifest field 'required_docs': expected a list of relative contract paths.")
        if not required_docs:
            raise ContractLoadError("Invalid export manifest field 'required_docs': list must not be empty.")
        validated: list[Path] = []
        for idx, doc_path in enumerate(required_docs):
            if not isinstance(doc_path, str) or not doc_path.strip():
                raise ContractLoadError(f"Invalid export manifest field 'required_docs[{idx}]': expected a non-empty relative path string.")
            validated.append(Path(doc_path))
        return validated

    @staticmethod
    def _resolve_git_sha(contract_repo_root: Path) -> str:
        try:
            top_level = subprocess.run(
                ["git", "rev-parse", "--show-toplevel"],
                cwd=contract_repo_root,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                text=True,
                check=True,
            ).stdout.strip()
            if Path(top_level).resolve() != contract_repo_root.resolve():
                raise subprocess.CalledProcessError(returncode=1, cmd=["git", "rev-parse", "--show-toplevel"], stderr="contract path is inside another git checkout, not the contract repo root")
            result = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                cwd=contract_repo_root,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                text=True,
                check=True,
            )
        except (OSError, subprocess.CalledProcessError) as exc:
            raise ContractLoadError(
                "Unable to resolve contract_version from the contract repo git SHA. EXCEPTIONS_LAKE_CONTRACT_REPO_PATH must point to an actual git checkout of LawFirm-os-semantic-substrate at the pinned commit. A plain ZIP/archive extraction without .git metadata is not a verifiable contract source for runtime execution."
            ) from exc
        return result.stdout.strip()

    @staticmethod
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

    @staticmethod
    def _git_ls_tree_blob_index(root: Path, commit_ref: str) -> dict[str, str]:
        """Map repo-relative paths to blob object ids at commit_ref (blobs only)."""
        try:
            raw = subprocess.run(
                ["git", "ls-tree", "-r", "-z", commit_ref],
                cwd=root,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                check=True,
            ).stdout
        except (OSError, subprocess.CalledProcessError) as exc:
            raise ContractLoadError(
                f"Cannot enumerate git tree at {commit_ref}. "
                "Ensure the Semantic Substrate checkout contains that commit."
            ) from exc
        index: dict[str, str] = {}
        for chunk in raw.split(b"\0"):
            if not chunk:
                continue
            chunk = chunk.rstrip(b"\r\n")
            if not chunk:
                continue
            match = _LS_TREE_ENTRY_Z.match(chunk)
            if not match:
                continue
            typ = match.group(2)
            if typ != b"blob":
                continue
            blob_sha = match.group(3).decode("ascii")
            path = match.group(4).decode("utf-8", errors="surrogateescape")
            path_norm = path.replace("\\", "/").lstrip("./")
            if path_norm:
                index[path_norm] = blob_sha
        return index

    @staticmethod
    def _git_read_blob(root: Path, blob_sha: str) -> bytes:
        try:
            return subprocess.run(
                ["git", "cat-file", "blob", blob_sha],
                cwd=root,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                check=True,
            ).stdout
        except subprocess.CalledProcessError as exc:
            raise ContractLoadError(f"Missing git blob {blob_sha} while reading committed contract surface.") from exc

    @staticmethod
    def _git_cat_file_batch(root: Path, object_ids: list[str]) -> dict[str, bytes]:
        """Read blob bytes for each object id (sequential cat-file calls; committed blob semantics)."""
        if not object_ids:
            return {}
        results: dict[str, bytes] = {}
        for oid in dict.fromkeys(object_ids):
            results[oid] = ContractLoader._git_read_blob(root, oid)
        return results

    @staticmethod
    def _git_dir(root: Path) -> Path | None:
        marker = root / ".git"
        if marker.is_dir():
            return marker
        if marker.is_file():
            text = marker.read_text(encoding="utf-8").strip()
            prefix = "gitdir:"
            if text.lower().startswith(prefix):
                git_path = Path(text[len(prefix) :].strip())
                return git_path if git_path.is_absolute() else (root / git_path).resolve()
        return None

    @classmethod
    def _git_object_exists(cls, root: Path, ref: str) -> bool:
        try:
            subprocess.run(
                ["git", "rev-parse", "--verify", f"{ref}^{{commit}}"],
                cwd=root,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=True,
            )
            return True
        except (OSError, subprocess.CalledProcessError):
            return False

    @classmethod
    def _compute_contract_surface_hash(
        cls,
        root: Path,
        *,
        surface_id: str,
        registry_path: str,
        commit_ref: str | None = None,
    ) -> str:
        """Compute surface digest; when commit_ref is set, hash git blob bytes at that commit (LF semantics)."""
        git_dir = cls._git_dir(root)
        use_git = commit_ref is not None and git_dir is not None
        blob_index: dict[str, str] | None = None
        registry: dict[str, Any]
        if use_git:
            assert commit_ref is not None
            blob_index = cls._git_ls_tree_blob_index(root, commit_ref)
            reg_oid = blob_index.get(registry_path)
            if reg_oid is None:
                raise ContractLoadError(
                    "Governed contract surface registry is missing from the pinned Semantic Substrate git commit "
                    f"(cannot read {registry_path} at {commit_ref}). "
                    "Ensure EXCEPTIONS_LAKE_CONTRACT_REPO_PATH is a full git checkout containing that commit, "
                    "or refresh contracts.lock.json."
                )
            registry_batch = cls._git_cat_file_batch(root, [reg_oid])
            registry_bytes = registry_batch[reg_oid]
            try:
                loaded = json.loads(registry_bytes.decode("utf-8"))
            except json.JSONDecodeError as exc:
                raise ContractLoadError(f"Governed contract surface registry at {registry_path} is not valid JSON at commit {commit_ref}: {exc}") from exc
            if not isinstance(loaded, dict):
                raise ContractLoadError(f"Governed contract surface registry at {registry_path} must be a JSON object at commit {commit_ref}.")
            registry = loaded
        else:
            registry = cls._read_json(root / registry_path)
        surface = None
        for candidate in registry.get("surfaces", []):
            if candidate.get("surface_id") == surface_id:
                surface = candidate
                break
        if surface is None:
            raise ContractLoadError(f"unknown contract surface id: {surface_id}")
        include_patterns = list(surface.get("include_patterns", []))
        exclude_patterns = list(surface.get("exclude_patterns", []))
        items: list[tuple[str, str, int]] = []
        if use_git:
            assert blob_index is not None
            matched_paths: list[str] = []
            for rel in sorted(blob_index):
                if any(part in {".git", "__pycache__", ".pytest_cache", ".ruff_cache"} for part in Path(rel).parts):
                    continue
                if not any(cls._matches(rel, pat) for pat in include_patterns):
                    continue
                if any(cls._matches(rel, pat) for pat in exclude_patterns):
                    continue
                matched_paths.append(rel)
            unique_blob_ids = list(dict.fromkeys(blob_index[rel] for rel in matched_paths))
            blob_payload = cls._git_cat_file_batch(root, unique_blob_ids)
            for rel in matched_paths:
                oid = blob_index[rel]
                data = blob_payload[oid]
                items.append((rel, hashlib.sha256(data).hexdigest(), len(data)))
        else:
            for path in sorted(root.rglob("*")):
                if not path.is_file():
                    continue
                rel = path.relative_to(root).as_posix()
                if any(part in {".git", "__pycache__", ".pytest_cache", ".ruff_cache"} for part in Path(rel).parts):
                    continue
                if not any(cls._matches(rel, pat) for pat in include_patterns):
                    continue
                if any(cls._matches(rel, pat) for pat in exclude_patterns):
                    continue
                data = path.read_bytes()
                items.append((rel, hashlib.sha256(data).hexdigest(), len(data)))
        if not items:
            raise ContractLoadError("contract surface selected zero files")
        digest = hashlib.sha256()
        digest.update(HASH_ALGORITHM.encode("utf-8"))
        digest.update(b"\0")
        digest.update(surface_id.encode("utf-8"))
        digest.update(b"\0")
        for rel, file_hash, size in items:
            digest.update(rel.encode("utf-8"))
            digest.update(b"\0")
            digest.update(file_hash.encode("ascii"))
            digest.update(b"\0")
            digest.update(str(size).encode("ascii"))
            digest.update(b"\0")
        return digest.hexdigest()

    @classmethod
    def _validate_contract_surface_lock(
        cls,
        contract_repo_root: Path,
        surface_lock: dict[str, Any],
        contract_lock: dict[str, Any],
    ) -> str:
        surface_id = surface_lock.get("surface_id")
        expected = surface_lock.get("surface_sha256")
        registry_path = surface_lock.get("surface_registry_path", "registry/contract-surface-registry.json")
        algorithm = surface_lock.get("hash_algorithm")
        if algorithm != HASH_ALGORITHM:
            raise ContractLoadError("contracts.lock.json contract_surface_lock.hash_algorithm is unsupported")
        if not isinstance(surface_id, str) or not surface_id.strip():
            raise ContractLoadError("contracts.lock.json contract_surface_lock.surface_id is missing")
        if not isinstance(expected, str) or len(expected) != 64:
            raise ContractLoadError("contracts.lock.json contract_surface_lock.surface_sha256 is invalid")
        if not isinstance(registry_path, str) or not registry_path.strip():
            raise ContractLoadError("contracts.lock.json contract_surface_lock.surface_registry_path is missing or invalid")

        locked_sha = contract_lock.get("contract_sha")
        if not isinstance(locked_sha, str) or len(locked_sha.strip()) != 40:
            raise ContractLoadError("contracts.lock.json contract_sha is invalid for contract_surface_lock validation")

        computed_raw = surface_lock.get("computed_from_commit")
        substrate_pin = contract_lock.get("substrate_repo_commit_sha")

        computed = computed_raw.strip() if isinstance(computed_raw, str) else ""
        substrate = substrate_pin.strip() if isinstance(substrate_pin, str) else ""

        if computed and substrate and computed != substrate:
            raise ContractLoadError(
                "contracts.lock.json substrate_repo_commit_sha does not match contract_surface_lock.computed_from_commit. "
                "Run scripts/update_contract_lock.py to regenerate a consistent lock."
            )
        if computed and computed != locked_sha.strip():
            raise ContractLoadError(
                "contracts.lock.json contract_sha must match contract_surface_lock.computed_from_commit when both are present. "
                "Run scripts/update_contract_lock.py to regenerate the lock."
            )
        if substrate and substrate != locked_sha.strip():
            raise ContractLoadError(
                "contracts.lock.json contract_sha must match substrate_repo_commit_sha when both are present. "
                "Run scripts/update_contract_lock.py to regenerate the lock."
            )

        fixture_mode = surface_lock.get("validation_source") == "working_tree_fixture"
        pin_committed_tree = bool(computed or substrate)

        rp = registry_path

        commit_ref: str | None
        if computed:
            commit_ref = computed
        elif substrate:
            commit_ref = substrate
        else:
            commit_ref = locked_sha.strip()

        if pin_committed_tree and not fixture_mode:
            git_dir = cls._git_dir(contract_repo_root)
            if git_dir is None:
                raise ContractLoadError(
                    "contracts.lock.json pins contract_surface_lock to committed Git tree bytes "
                    "(substrate_repo_commit_sha / computed_from_commit), but EXCEPTIONS_LAKE_CONTRACT_REPO_PATH "
                    "is not a git checkout. Use a full Semantic Substrate clone, or set "
                    "contract_surface_lock.validation_source to \"working_tree_fixture\" only for governed local fixtures."
                )
            if not cls._git_object_exists(contract_repo_root, commit_ref):
                raise ContractLoadError(
                    f"Pinned Semantic Substrate commit {commit_ref} is not present in the contract repo git object database. "
                    "Fetch that commit from origin or point EXCEPTIONS_LAKE_CONTRACT_REPO_PATH at a checkout that contains it."
                )
            observed = cls._compute_contract_surface_hash(
                contract_repo_root,
                surface_id=surface_id,
                registry_path=rp,
                commit_ref=commit_ref,
            )
        else:
            observed = cls._compute_contract_surface_hash(
                contract_repo_root,
                surface_id=surface_id,
                registry_path=rp,
                commit_ref=None,
            )

        if observed != expected:
            raise ContractLoadError(
                f"Committed contract surface hash {observed} does not match contracts.lock.json surface hash {expected}. "
                "Run scripts/update_contract_lock.py to refresh the pin."
            )
        return observed
