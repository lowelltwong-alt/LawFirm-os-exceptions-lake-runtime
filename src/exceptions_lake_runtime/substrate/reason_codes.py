"""Substrate-owned controlled vocabulary, loaded fail-closed for the
exception lake runtime (PR-05.5).

Mirrors the orchestrator's loader. The lake does not invent
admission_reason_code or defect_class values. They are read from the
substrate's ``registry/runtime-reason-codes-registry.json`` at import time.

If the substrate is not available or the registry is malformed, this module
raises at import. That is the desired behavior.

Discovery order for substrate location:

1. ``LFOS_SUBSTRATE_PATH`` environment variable, if set.
2. ``EXCEPTIONS_LAKE_CONTRACT_REPO_PATH`` env var (lake's existing convention).
3. ``<lake-repo>/../<contract_repo>`` derived from this repo's
   ``contracts.lock.json``.
4. ``<lake-repo>/../LawFirm-os-semantic-substrate`` as a final fallback.

No silent hardcoded fallback list. No "invent if substrate unavailable" path.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Mapping

_REPO_ROOT = Path(__file__).resolve().parents[3]
_LOCK_PATH = _REPO_ROOT / "contracts.lock.json"


class ReasonCodeRegistryError(RuntimeError):
    """Raised when the substrate controlled-vocabulary registry cannot be loaded."""


def _resolve_substrate_root() -> Path:
    for env_var in ("LFOS_SUBSTRATE_PATH", "EXCEPTIONS_LAKE_CONTRACT_REPO_PATH"):
        override = os.environ.get(env_var)
        if override:
            candidate = Path(override)
            if candidate.is_dir():
                return candidate
            raise ReasonCodeRegistryError(
                f"{env_var} points to a non-directory: {override}"
            )
    if _LOCK_PATH.is_file():
        try:
            lock = json.loads(_LOCK_PATH.read_text(encoding="utf-8"))
            contract_repo = lock.get("contract_repo")
        except (json.JSONDecodeError, OSError) as exc:
            raise ReasonCodeRegistryError(
                f"cannot read lake contracts.lock.json at {_LOCK_PATH}: {exc}"
            ) from exc
        if isinstance(contract_repo, str) and contract_repo:
            candidate = _REPO_ROOT.parent / contract_repo
            if candidate.is_dir():
                return candidate
    fallback = _REPO_ROOT.parent / "LawFirm-os-semantic-substrate"
    if fallback.is_dir():
        return fallback
    raise ReasonCodeRegistryError(
        "substrate repo not discoverable; set LFOS_SUBSTRATE_PATH or place the "
        "substrate as a sibling of the exception-lake repo"
    )


def _load_vocabularies(substrate_root: Path) -> Mapping[str, frozenset[str]]:
    registry_path = substrate_root / "registry" / "runtime-reason-codes-registry.json"
    if not registry_path.is_file():
        raise ReasonCodeRegistryError(
            f"runtime-reason-codes-registry.json not found at {registry_path}; "
            "exception lake cannot operate without the substrate controlled vocabulary"
        )
    try:
        raw = json.loads(registry_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ReasonCodeRegistryError(
            f"runtime-reason-codes-registry.json is not valid JSON: {exc}"
        ) from exc
    vocabs = raw.get("vocabularies")
    if not isinstance(vocabs, dict):
        raise ReasonCodeRegistryError(
            "runtime-reason-codes-registry.json is missing a 'vocabularies' object"
        )
    result: dict[str, frozenset[str]] = {}
    for name, body in vocabs.items():
        values = body.get("values") if isinstance(body, dict) else None
        if not isinstance(values, list) or not all(isinstance(v, str) for v in values):
            raise ReasonCodeRegistryError(
                f"vocabulary {name!r} is missing a list of string values"
            )
        result[name] = frozenset(values)
    return result


_VOCABS = _load_vocabularies(_resolve_substrate_root())


def _require(vocab: str, value: str) -> str:
    allowed = _VOCABS.get(vocab, frozenset())
    if value not in allowed:
        raise ReasonCodeRegistryError(
            f"{value!r} is not registered in vocabulary {vocab!r}"
        )
    return value


# ---------- ExceptionLakeAdmissionRecord.admission_reason_code constants ----------

_ADM = "exception_lake.admission_reason_codes"

PASSED_DRY_RUN_ADMISSION = _require(_ADM, "passed_dry_run_admission")
WRONG_PACKET_SCHEMA = _require(_ADM, "wrong_packet_schema")
MISSING_CONTRACT_SURFACE = _require(_ADM, "missing_contract_surface")
CONTRACT_SURFACE_MISMATCH = _require(_ADM, "contract_surface_mismatch")
MISSING_CONTEXT_BUNDLE_REF = _require(_ADM, "missing_context_bundle_ref")
MISSING_EXECUTION_AUTHORITY = _require(_ADM, "missing_execution_authority")
PACKET_HASH_MISMATCH = _require(_ADM, "packet_hash_mismatch")

EXCEPTION_LAKE_ADMISSION_REASON_CODES: frozenset[str] = _VOCABS[_ADM]


# ---------- DefectRecord.defect_class constants (PR-06 forward-compat) ----------

DEFECT_CLASSES: frozenset[str] = _VOCABS["defect_record.defect_classes"]


# ---------- helpers ----------

def is_registered_admission_reason_code(value: str) -> bool:
    return value in EXCEPTION_LAKE_ADMISSION_REASON_CODES


def is_registered_defect_class(value: str) -> bool:
    return value in DEFECT_CLASSES
