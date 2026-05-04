from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path

from exceptions_lake_runtime.cli import main
from exceptions_lake_runtime.contract_loader import CONTRACT_LOCK_RELATIVE_PATH


def _snapshot_repo_contents(root: Path) -> dict[str, str]:
    snapshot: dict[str, str] = {}
    for file_path in sorted(root.rglob("*")):
        if not file_path.is_file():
            continue
        if ".git" in file_path.parts:
            continue
        digest = hashlib.sha256(file_path.read_bytes()).hexdigest()
        snapshot[str(file_path.relative_to(root))] = digest
    return snapshot


def _git_sha(path: Path) -> str:
    return subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=path,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def _lock_path(runtime_repo_root: Path) -> Path:
    return runtime_repo_root / CONTRACT_LOCK_RELATIVE_PATH


def test_cli_health_returns_success(
    runtime_config, monkeypatch, capsys
) -> None:
    monkeypatch.chdir(runtime_config.runtime_data_dir.parent)

    exit_code = main(["health"])

    captured = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert captured["runtime_status"] == "ready"
    assert captured["contract_repo_available"] is True
    assert captured["contract_version"] == _git_sha(runtime_config.contract_repo_root)
    assert captured["locked_contract_sha"] == captured["contract_version"]
    assert captured["non_production"] is True


def test_cli_ingest_synthetic_accepts_example_and_stores_event(
    runtime_config, runtime_repo_root: Path, monkeypatch, capsys
) -> None:
    monkeypatch.chdir(runtime_config.runtime_data_dir.parent)
    example_path = runtime_repo_root / "examples" / "synthetic_exception_event.json"

    exit_code = main(["ingest-synthetic", str(example_path)])

    captured = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert captured["accepted"] is True
    assert captured["stored"] is True
    event_lines = runtime_config.event_store_path.read_text(encoding="utf-8").splitlines()
    assert len(event_lines) == 1


def test_cli_list_events_returns_stored_events(
    runtime_config, runtime_repo_root: Path, monkeypatch, capsys
) -> None:
    monkeypatch.chdir(runtime_config.runtime_data_dir.parent)
    example_path = runtime_repo_root / "examples" / "synthetic_exception_event.json"
    assert main(["ingest-synthetic", str(example_path)]) == 0
    capsys.readouterr()

    exit_code = main(["list-events"])

    captured = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert len(captured) == 1
    assert captured[0]["event_id"] == "EXC-900001"


def test_cli_build_pressure_candidate_returns_non_canonical_candidate(
    runtime_config, runtime_repo_root: Path, monkeypatch, capsys
) -> None:
    monkeypatch.chdir(runtime_config.runtime_data_dir.parent)
    example_path = runtime_repo_root / "examples" / "synthetic_exception_event.json"
    assert main(["ingest-synthetic", str(example_path)]) == 0
    capsys.readouterr()

    exit_code = main(["build-pressure-candidate"])

    captured = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert captured["candidate_status"] == "synthetic_candidate_not_canonical"


def test_cli_non_synthetic_preflight_passes_with_complete_approved_metadata(
    runtime_config,
    non_synthetic_readiness_request: dict,
    monkeypatch,
    tmp_path: Path,
    capsys,
) -> None:
    monkeypatch.chdir(runtime_config.runtime_data_dir.parent)
    readiness_path = tmp_path / "readiness.json"
    readiness_path.write_text(
        json.dumps(non_synthetic_readiness_request, indent=2) + "\n",
        encoding="utf-8",
    )

    exit_code = main(["non-synthetic-preflight", str(readiness_path)])

    captured = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert captured["mode"] == "non_synthetic_dry_run_preflight"
    assert captured["preflight_ready"] is True


def test_cli_non_synthetic_preflight_does_not_append_to_event_store(
    runtime_config,
    non_synthetic_readiness_request: dict,
    monkeypatch,
    tmp_path: Path,
    capsys,
) -> None:
    monkeypatch.chdir(runtime_config.runtime_data_dir.parent)
    readiness_path = tmp_path / "readiness.json"
    readiness_path.write_text(
        json.dumps(non_synthetic_readiness_request, indent=2) + "\n",
        encoding="utf-8",
    )

    exit_code = main(["non-synthetic-preflight", str(readiness_path)])

    _ = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert runtime_config.event_store_path.exists() is False


def test_cli_rejects_production_or_live_connector_flags(
    runtime_config, runtime_repo_root: Path, monkeypatch, tmp_path: Path, capsys
) -> None:
    monkeypatch.chdir(runtime_config.runtime_data_dir.parent)
    payload = json.loads(
        (runtime_repo_root / "examples" / "synthetic_exception_event.json").read_text(
            encoding="utf-8"
        )
    )
    envelope = {
        "ingestion_mode": "synthetic_test_only",
        "actor": "synthetic-test-runner",
        "data_flags": {
            "production": True,
            "real_client_data": False,
            "real_matter_data": False,
            "live_connector": False,
        },
        "payload": payload,
    }
    envelope_path = tmp_path / "denied-envelope.json"
    envelope_path.write_text(json.dumps(envelope, indent=2) + "\n", encoding="utf-8")

    exit_code = main(["ingest-synthetic", str(envelope_path)])

    captured = json.loads(capsys.readouterr().out)
    assert exit_code == 1
    assert captured["policy_result"]["allowed"] is False
    assert captured["stored"] is False


def test_cli_refresh_contract_lock_writes_only_runtime_repo_lock(
    runtime_config, runtime_repo_root: Path, monkeypatch, capsys
) -> None:
    monkeypatch.chdir(runtime_config.runtime_data_dir.parent)
    before_contract_snapshot = _snapshot_repo_contents(runtime_config.contract_repo_root)
    before_lock = json.loads(_lock_path(runtime_repo_root).read_text(encoding="utf-8"))

    exit_code = main(["refresh-contract-lock"])

    captured = json.loads(capsys.readouterr().out)
    after_lock = json.loads(_lock_path(runtime_repo_root).read_text(encoding="utf-8"))
    after_contract_snapshot = _snapshot_repo_contents(runtime_config.contract_repo_root)

    assert exit_code == 0
    assert captured["locked_contract_sha"] == _git_sha(runtime_config.contract_repo_root)
    assert after_lock["contract_sha"] == captured["locked_contract_sha"]
    assert after_lock["contract_repo"] == before_lock["contract_repo"]
    assert before_contract_snapshot == after_contract_snapshot
