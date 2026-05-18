"""Tests for the lake-side substrate reason-codes loader (PR-05.5)."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC = REPO_ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from exceptions_lake_runtime.substrate import reason_codes as rc  # noqa: E402

SUBSTRATE = REPO_ROOT.parent / "LawFirm-os-semantic-substrate"
REGISTRY = SUBSTRATE / "registry" / "runtime-reason-codes-registry.json"


def _registry_vocab(name: str) -> set[str]:
    return set(json.loads(REGISTRY.read_text(encoding="utf-8"))["vocabularies"][name]["values"])


def test_module_imports_only_when_substrate_registry_exists() -> None:
    assert hasattr(rc, "EXCEPTION_LAKE_ADMISSION_REASON_CODES")
    assert hasattr(rc, "DEFECT_CLASSES")


def test_constants_match_registry_admission_reason_codes() -> None:
    expected = _registry_vocab("exception_lake.admission_reason_codes")
    assert rc.EXCEPTION_LAKE_ADMISSION_REASON_CODES == frozenset(expected)
    for value in expected:
        const_name = value.upper()
        assert getattr(rc, const_name) == value, f"{const_name} must equal {value!r}"


def test_defect_classes_match_registry() -> None:
    expected = _registry_vocab("defect_record.defect_classes")
    assert rc.DEFECT_CLASSES == frozenset(expected)


def test_helpers_recognise_registered_values() -> None:
    for v in rc.EXCEPTION_LAKE_ADMISSION_REASON_CODES:
        assert rc.is_registered_admission_reason_code(v) is True
    for v in rc.DEFECT_CLASSES:
        assert rc.is_registered_defect_class(v) is True
    assert rc.is_registered_admission_reason_code("invented") is False
    assert rc.is_registered_defect_class("invented") is False


def test_loader_raises_for_missing_registry(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    fake_substrate = tmp_path / "fake-substrate"
    fake_substrate.mkdir()
    monkeypatch.setenv("LFOS_SUBSTRATE_PATH", str(fake_substrate))
    import importlib
    sys.modules.pop("exceptions_lake_runtime.substrate.reason_codes", None)
    with pytest.raises(Exception) as exc_info:
        importlib.import_module("exceptions_lake_runtime.substrate.reason_codes")
    assert "runtime-reason-codes-registry" in str(exc_info.value)
