from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import yaml

from scripts import run_full_pytest


REPO_ROOT = Path(__file__).resolve().parents[1]
POLICY_PATH = REPO_ROOT / "config" / "validation-runtime-policy.yaml"


def _load_policy() -> dict:
    policy = yaml.safe_load(POLICY_PATH.read_text(encoding="utf-8"))
    assert isinstance(policy, dict)
    return policy


def test_validation_runtime_policy_requires_long_python_test_ceilings() -> None:
    commands = _load_policy()["commands"]

    assert commands["full_pytest"]["minimum_timeout_seconds"] >= 3600
    assert commands["focused_pytest"]["minimum_timeout_seconds"] >= 3600
    assert "scripts/run_full_pytest.py" in commands["full_pytest"]["wrapper"]
    assert "scripts/run_full_pytest.py" in commands["focused_pytest"]["wrapper"]


def test_pytest_wrapper_reads_validation_runtime_policy() -> None:
    assert run_full_pytest.POLICY_PATH == POLICY_PATH
    assert run_full_pytest.pytest_timeout_seconds() >= 3600
    assert run_full_pytest.pytest_timeout_seconds("focused_pytest") >= 3600


def test_pytest_wrapper_sets_policy_marker() -> None:
    env = run_full_pytest.validation_environment({})

    assert (
        env[run_full_pytest.POLICY_MARKER_ENV_VAR]
        == run_full_pytest.POLICY_MARKER_VALUE
    )
    assert env["PYTHONDONTWRITEBYTECODE"] == "1"
    assert env["PYTHONPATH"].split(os.pathsep)[0] == str(REPO_ROOT / "src")
    assert run_full_pytest.sys.dont_write_bytecode is True


def test_pytest_wrapper_disables_pytest_cache_provider() -> None:
    command = run_full_pytest.pytest_command(
        ["tests/test_validation_runtime_policy.py", "-q"]
    )

    assert command[1:6] == ["-B", "-m", "pytest", "-p", "no:cacheprovider"]


def test_direct_pytest_without_policy_marker_fails_closed() -> None:
    env = dict(os.environ)
    env.pop(run_full_pytest.POLICY_MARKER_ENV_VAR, None)
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            "--collect-only",
            "tests/test_validation_runtime_policy.py",
        ],
        cwd=REPO_ROOT,
        env=env,
        capture_output=True,
        check=False,
        text=True,
        timeout=30,
    )

    assert completed.returncode == 4
    output = f"{completed.stdout}\n{completed.stderr}"
    assert (
        "Direct pytest invocation is blocked by the validation runtime policy" in output
    )


def test_agent_docs_reference_pytest_policy_wrapper() -> None:
    docs = "\n".join(
        [
            (REPO_ROOT / "AGENTS.md").read_text(encoding="utf-8"),
            (REPO_ROOT / "AI_WORK_START_HERE.md").read_text(encoding="utf-8"),
            (REPO_ROOT / "README.md").read_text(encoding="utf-8"),
            (REPO_ROOT / "ENDPOINTS_AND_COMMANDS.md").read_text(encoding="utf-8"),
            (REPO_ROOT / "docs" / "LOCAL_DEV.md").read_text(encoding="utf-8"),
        ]
    )

    assert "python scripts/run_full_pytest.py" in docs
    assert "validation-runtime-policy.yaml" in docs


def test_ci_manifest_uses_pytest_policy_wrapper() -> None:
    manifest = json.loads(
        (REPO_ROOT / "ci-test-manifest.json").read_text(encoding="utf-8")
    )
    runner_commands = [
        artifact["runner_command"]
        for artifact in manifest["test_artifacts"]
        if artifact.get("framework") == "pytest"
    ]

    assert runner_commands
    assert all(
        command.startswith("python scripts/run_full_pytest.py")
        for command in runner_commands
    )
    assert not any(
        command.startswith("python -m pytest") for command in runner_commands
    )
