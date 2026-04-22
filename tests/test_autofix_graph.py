"""Tests for agent_tools.autofix_graph."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest

from agent_tools.autofix_graph import (
    AutoFixState,
    analyze_failure_node,
    apply_fix,
    build_result_json,
    collect_error,
    decide_next,
    generate_fix,
    run_autofix,
    run_tests,
)


SAMPLE_CI_INPUT = """\
# Debug Agent Input

## Build
- Job: cicd-practice-app
- Build number: 48

## Changed Files
app/main.py

## Pytest Output
FAILED tests/test_main.py::test_read_root - AssertionError: assert {'message': 'broken'} == {'message': 'hello cicd'}
E       AssertionError: assert {'message': 'broken'} == {'message': 'hello cicd'}
"""

BROKEN_MAIN_PY = '''\
from fastapi import FastAPI

app = FastAPI(title="CI/CD Practice App")


@app.get("/")
def read_root():
    return {"message": "broken"}


@app.get("/health")
def health_check():
    return {"status": "ok"}
'''

FIXED_MAIN_PY = '''\
from fastapi import FastAPI

app = FastAPI(title="CI/CD Practice App")


@app.get("/")
def read_root():
    return {"message": "hello cicd"}


@app.get("/health")
def health_check():
    return {"status": "ok"}
'''


@pytest.fixture()
def workspace(tmp_path: Path) -> Path:
    """Set up a minimal workspace with broken app/main.py."""
    app_dir = tmp_path / "app"
    app_dir.mkdir()
    (app_dir / "__init__.py").write_text("", encoding="utf-8")
    (app_dir / "main.py").write_text(BROKEN_MAIN_PY, encoding="utf-8")

    tests_dir = tmp_path / "tests"
    tests_dir.mkdir()
    (tests_dir / "test_main.py").write_text(
        'from fastapi.testclient import TestClient\n'
        'from app.main import app\n'
        'client = TestClient(app)\n'
        'def test_read_root():\n'
        '    response = client.get("/")\n'
        '    assert response.status_code == 200\n'
        '    assert response.json() == {"message": "hello cicd"}\n'
        'def test_health_check():\n'
        '    response = client.get("/health")\n'
        '    assert response.status_code == 200\n'
        '    assert response.json() == {"status": "ok"}\n',
        encoding="utf-8",
    )

    ci_input_path = tmp_path / "debug-agent-input.md"
    ci_input_path.write_text(SAMPLE_CI_INPUT, encoding="utf-8")

    # Create prompt files
    prompts_dir = tmp_path / "prompts"
    prompts_dir.mkdir()
    (prompts_dir / "debug-agent-system.md").write_text("Test system prompt.", encoding="utf-8")
    (prompts_dir / "debug-agent-user.md").write_text("Analyze: {{DEBUG_AGENT_INPUT}}", encoding="utf-8")

    return tmp_path


def _make_state(workspace: Path) -> AutoFixState:
    return {
        "input_path": str(workspace / "debug-agent-input.md"),
        "workspace": str(workspace),
        "system_prompt_path": str(workspace / "prompts" / "debug-agent-system.md"),
        "user_prompt_path": str(workspace / "prompts" / "debug-agent-user.md"),
        "max_attempts": 3,
    }


def test_collect_error(workspace: Path) -> None:
    state = _make_state(workspace)
    state = collect_error(state)
    assert "Debug Agent Input" in state["ci_input"]
    assert state["system_prompt"]
    assert state["rendered_user_prompt"]


def test_analyze_failure_node(workspace: Path) -> None:
    state = _make_state(workspace)
    state = collect_error(state)
    state = analyze_failure_node(state)
    assert "failed_tests" in state["analysis"]
    assert len(state["analysis"]["failed_tests"]) > 0


def test_generate_fix_rule_based(workspace: Path) -> None:
    state = _make_state(workspace)
    state = collect_error(state)
    state = analyze_failure_node(state)
    state = generate_fix(state)
    assert state["patch_candidate"] is not None
    assert state["patch_candidate"]["kind"] == "replace_text"
    assert state["patch_candidate"]["target_file"] == "app/main.py"


def test_apply_fix(workspace: Path) -> None:
    state = _make_state(workspace)
    state = collect_error(state)
    state = analyze_failure_node(state)
    state = generate_fix(state)
    state = apply_fix(state)
    assert state["patch_result"]["applied"] is True

    fixed_content = (workspace / "app" / "main.py").read_text(encoding="utf-8")
    assert '"hello cicd"' in fixed_content


def test_run_tests_after_fix(workspace: Path) -> None:
    """After applying fix, pytest should pass."""
    state = _make_state(workspace)
    state = collect_error(state)
    state = analyze_failure_node(state)
    state = generate_fix(state)
    state = apply_fix(state)
    state = run_tests(state)
    assert state["test_passed"] is True


def test_decide_next_commit(workspace: Path) -> None:
    state = _make_state(workspace)
    state["attempt"] = 0
    state["test_passed"] = True
    state["action"] = ""
    state["attempts_history"] = []
    state["patch_candidate"] = {"kind": "replace_text"}
    state["test_log"] = "all passed"
    state = decide_next(state)
    assert state["action"] == "commit_push"


def test_decide_next_retry() -> None:
    state: AutoFixState = {
        "attempt": 0,
        "max_attempts": 3,
        "test_passed": False,
        "action": "",
        "attempts_history": [],
        "patch_candidate": {"kind": "replace_text"},
        "test_log": "FAILED",
    }
    state = decide_next(state)
    assert state["action"] == "retry"


def test_decide_next_give_up() -> None:
    state: AutoFixState = {
        "attempt": 2,
        "max_attempts": 3,
        "test_passed": False,
        "action": "",
        "attempts_history": [],
        "patch_candidate": {"kind": "replace_text"},
        "test_log": "FAILED",
    }
    state = decide_next(state)
    assert state["action"] == "give_up"


def test_run_autofix_full_success(workspace: Path) -> None:
    """Full end-to-end: broken code → auto-fix → tests pass → commit_push."""
    state = _make_state(workspace)
    final = run_autofix(state)
    assert final["action"] == "commit_push"
    assert final["test_passed"] is True
    assert final["attempt"] == 0  # Fixed on first try

    # File should be fixed
    fixed_content = (workspace / "app" / "main.py").read_text(encoding="utf-8")
    assert '"hello cicd"' in fixed_content


def test_run_autofix_no_patch(workspace: Path) -> None:
    """If CI input has no recognizable pattern, agent gives up."""
    ci_input = "# Empty CI input\nNo useful error info here.\n"
    (workspace / "debug-agent-input.md").write_text(ci_input, encoding="utf-8")

    state = _make_state(workspace)
    final = run_autofix(state)
    assert final["action"] == "give_up"


def test_build_result_json(workspace: Path) -> None:
    state = _make_state(workspace)
    final = run_autofix(state)
    result = build_result_json(final)
    assert "action" in result
    assert "test_passed" in result
    assert "attempts_history" in result
    assert isinstance(result["attempts_history"], list)
