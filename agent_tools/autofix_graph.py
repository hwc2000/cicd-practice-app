"""Auto-fix CI loop: collect error → analyze → generate fix → apply → test → retry or commit.

This module runs entirely within the Jenkins workspace. It does NOT push or
deploy — the Jenkinsfile handles git commit/push and rebuild triggering after
this script reports ``action == "commit_push"``.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any, TypedDict


from agent_tools.failure_context import (
    DEFAULT_SYSTEM_PROMPT,
    DEFAULT_USER_PROMPT,
    analyze_ci_failure,
    read_prompt,
    render_user_prompt,
)
from agent_tools.patch_candidate import apply_patch_candidate


class AutoFixState(TypedDict, total=False):
    # --- inputs ---
    input_path: str
    workspace: str
    system_prompt_path: str
    user_prompt_path: str
    env_file: str
    max_attempts: int

    # --- collected ---
    ci_input: str
    system_prompt: str
    user_prompt_template: str
    rendered_user_prompt: str

    # --- per-attempt ---
    attempt: int
    analysis: dict[str, Any]
    patch_candidate: dict[str, Any] | None
    patch_result: dict[str, Any] | None
    test_passed: bool
    test_log: str

    # --- decision ---
    action: str  # "commit_push" | "retry" | "give_up" | "no_fix"
    summary: str

    # --- history ---
    attempts_history: list[dict[str, Any]]


# ---------------------------------------------------------------------------
# Nodes
# ---------------------------------------------------------------------------


def collect_error(state: AutoFixState) -> AutoFixState:
    """Read CI failure artifacts and prompt templates."""
    input_path = Path(state["input_path"])
    state["ci_input"] = input_path.read_text(encoding="utf-8")
    state["system_prompt"] = read_prompt(
        Path(state.get("system_prompt_path", str(DEFAULT_SYSTEM_PROMPT))),
    )
    state["user_prompt_template"] = read_prompt(
        Path(state.get("user_prompt_path", str(DEFAULT_USER_PROMPT))),
    )
    state["rendered_user_prompt"] = render_user_prompt(
        state["user_prompt_template"],
        state["ci_input"],
    )
    state.setdefault("attempts_history", [])
    return state


def analyze_failure_node(state: AutoFixState) -> AutoFixState:
    """Extract reusable failure context for later repair steps."""
    state["analysis"] = analyze_ci_failure(
        input_text=state["ci_input"],
        system_prompt=state["system_prompt"],
        user_prompt=state["rendered_user_prompt"],
    )
    return state


def generate_fix(state: AutoFixState) -> AutoFixState:
    """Generate patch_candidate — try OpenAI first, fall back to rule-based."""
    analysis = state["analysis"]

    # 1) OpenAI (if configured)
    openai_patch = _try_openai_fix(state)
    if openai_patch:
        state["patch_candidate"] = openai_patch
        return state

    # 2) Rule-based fallback
    state["patch_candidate"] = analysis.get("patch_candidate")
    return state


def apply_fix(state: AutoFixState) -> AutoFixState:
    """Apply patch_candidate to the workspace file."""
    patch = state.get("patch_candidate")
    if not patch:
        state["patch_result"] = None
        state["action"] = "no_fix"
        return state

    try:
        workspace = Path(state.get("workspace", "."))
        result = apply_patch_candidate(patch, workspace=workspace, apply=True)
        state["patch_result"] = result
    except (ValueError, FileNotFoundError) as exc:
        state["patch_result"] = {"applied": False, "error": str(exc)}
        state["action"] = "no_fix"

    return state


def run_tests(state: AutoFixState) -> AutoFixState:
    """Run pytest locally to verify the fix."""
    if state.get("action") in ("no_fix", "give_up"):
        state["test_passed"] = False
        state["test_log"] = "Skipped: no fix was applied."
        return state

    workspace = state.get("workspace", ".")
    env = {**os.environ, "PYTHONPATH": "."}
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "-q"],
        capture_output=True,
        text=True,
        cwd=workspace,
        env=env,
    )

    state["test_passed"] = result.returncode == 0
    state["test_log"] = (result.stdout + result.stderr).strip()
    return state


def decide_next(state: AutoFixState) -> AutoFixState:
    """Decide: commit_push, retry, or give_up."""
    attempt = state.get("attempt", 0)
    max_attempts = state.get("max_attempts", 3)

    # Record this attempt
    state["attempts_history"].append({
        "attempt": attempt,
        "test_passed": state.get("test_passed", False),
        "action": state.get("action", ""),
        "patch_candidate": state.get("patch_candidate"),
        "test_log_preview": (state.get("test_log") or "")[:500],
    })

    if state.get("action") == "no_fix":
        state["action"] = "give_up"
        state["summary"] = f"Attempt {attempt + 1}: no patch candidate was generated."
        return state

    if state.get("test_passed"):
        state["action"] = "commit_push"
        state["summary"] = f"Fix verified on attempt {attempt + 1}."
        return state

    if attempt + 1 < max_attempts:
        state["action"] = "retry"
        state["summary"] = f"Attempt {attempt + 1} failed. Will retry."
    else:
        state["action"] = "give_up"
        state["summary"] = f"All {max_attempts} attempts exhausted. Manual review required."

    return state


# ---------------------------------------------------------------------------
# OpenAI helper
# ---------------------------------------------------------------------------


def _try_openai_fix(state: AutoFixState) -> dict[str, Any] | None:
    """Try to get a patch_candidate via OpenAI with actual source code context.

    Reads the suspected files from the workspace and sends their content to
    OpenAI along with the error analysis, so the LLM can generate a precise
    find/replace patch for any failure pattern it can understand.
    """
    try:
        from agent_tools.openai_repair import (
            generate_openai_patch,
            load_config,
            merged_env,
        )

        env_file = Path(state.get("env_file", ".env"))
        config = load_config(merged_env(env_file))
        if not config.enabled or not config.api_key:
            return None

        # Read suspected source files from workspace
        analysis = state.get("analysis", {})
        suspected_files = analysis.get("suspected_files", [])
        failed_tests = analysis.get("failed_tests", [])
        workspace = Path(state.get("workspace", "."))

        file_contents: dict[str, str] = {}

        # Add suspected files
        for filepath in suspected_files:
            full_path = workspace / filepath
            if full_path.exists():
                file_contents[filepath] = full_path.read_text(encoding="utf-8")

        # Also add failing test files (so LLM sees what the test expects)
        for test_id in failed_tests:
            test_file = test_id.split("::", 1)[0]  # "tests/test_main.py::test_read_root" -> "tests/test_main.py"
            if test_file not in file_contents:
                full_path = workspace / test_file
                if full_path.exists():
                    file_contents[test_file] = full_path.read_text(encoding="utf-8")

        if not file_contents:
            return None

        return generate_openai_patch(
            ci_input=state["ci_input"],
            suspected_files=file_contents,
            analysis=analysis,
            config=config,
        )
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Graph runner (with retry loop)
# ---------------------------------------------------------------------------


def run_autofix(initial_state: AutoFixState) -> AutoFixState:
    """Execute the auto-fix loop with retry support."""
    state: AutoFixState = {**initial_state}
    max_attempts = state.get("max_attempts", 3)

    # Collect inputs once
    state = collect_error(state)

    workspace = Path(state.get("workspace", "."))

    for attempt in range(max_attempts):
        state["attempt"] = attempt
        # Reset per-attempt fields
        state["action"] = ""
        state["patch_candidate"] = None
        state["patch_result"] = None
        state["test_passed"] = False
        state["test_log"] = ""

        # Analyze
        state = analyze_failure_node(state)

        # Generate fix
        state = generate_fix(state)

        if not state.get("patch_candidate"):
            state["action"] = "no_fix"
            state = decide_next(state)
            break

        # Apply fix
        state = apply_fix(state)
        if state.get("action") == "no_fix":
            state = decide_next(state)
            break

        # Run tests
        state = run_tests(state)

        # Decide
        state = decide_next(state)

        if state["action"] == "commit_push":
            break

        if state["action"] == "give_up":
            break

        if state["action"] == "retry":
            # Keep the current workspace changes so later attempts can build on
            # earlier partial fixes when multiple issues are chained together.
            state["ci_input"] += (
                f"\n\n## Auto-Fix Attempt {attempt + 1} (failed)\n"
                f"Patch applied: {json.dumps(state.get('patch_result'), ensure_ascii=False)}\n"
                f"Test output:\n```\n{state.get('test_log', '')[:1000]}\n```\n"
            )
            state["rendered_user_prompt"] = render_user_prompt(
                state["user_prompt_template"],
                state["ci_input"],
            )

    return state


# ---------------------------------------------------------------------------
# JSON output
# ---------------------------------------------------------------------------


def build_result_json(state: AutoFixState) -> dict[str, Any]:
    """Build the JSON result for Jenkinsfile consumption."""
    return {
        "action": state.get("action", "give_up"),
        "test_passed": state.get("test_passed", False),
        "attempt": state.get("attempt", 0),
        "max_attempts": state.get("max_attempts", 3),
        "summary": state.get("summary", ""),
        "patch_result": state.get("patch_result"),
        "attempts_history": state.get("attempts_history", []),
    }
