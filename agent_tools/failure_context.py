"""Reusable CI failure-context extraction and report rendering utilities.

This module is intentionally app-agnostic so it can be reused by:

- the current Jenkins auto-fix pipeline
- a future multi-agent coordinator
- a service/API that accepts CI artifacts from other apps
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any


DEFAULT_SYSTEM_PROMPT = Path("prompts/debug-agent-system.md")
DEFAULT_USER_PROMPT = Path("prompts/debug-agent-user.md")


def read_prompt(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8").strip()


def render_user_prompt(template: str, input_text: str) -> str:
    return template.replace("{{DEBUG_AGENT_INPUT}}", input_text.strip())


def summarize_prompt(system_prompt: str, user_prompt: str) -> str:
    if not system_prompt and not user_prompt:
        return "No prompt files were loaded."

    sections = []
    if system_prompt:
        sections.append(f"System prompt: {len(system_prompt.split())} words")
    if user_prompt:
        sections.append(f"User prompt: {len(user_prompt.split())} words")
    return "\n".join(sections)


def extract_section(text: str, heading: str) -> str:
    pattern = rf"^## {re.escape(heading)}\n(?P<body>.*?)(?=^## |\Z)"
    match = re.search(pattern, text, re.MULTILINE | re.DOTALL)
    if not match:
        return ""
    return match.group("body").strip()


def unique_lines(lines: list[str]) -> list[str]:
    seen = set()
    result = []
    for line in lines:
        value = line.strip()
        if value and value not in seen:
            seen.add(value)
            result.append(value)
    return result


def extract_failed_tests(text: str) -> list[str]:
    tests = re.findall(r"^(?:FAILED\s+)?(tests/[^\s]+::[^\s]+)", text, re.MULTILINE)
    return unique_lines(tests)


def extract_error_lines(text: str) -> list[str]:
    error_lines = re.findall(r"^E\s+(.+)$", text, re.MULTILINE)
    if error_lines:
        return unique_lines(error_lines[:5])

    fallback = re.findall(r"^(AssertionError:.+|[A-Za-z_]+Error:.+)$", text, re.MULTILINE)
    return unique_lines(fallback[:5])


def extract_changed_files(text: str) -> list[str]:
    changed_section = extract_section(text, "Changed Files")
    candidates = changed_section.splitlines() if changed_section else text.splitlines()
    files = [
        line.strip()
        for line in candidates
        if re.match(r"^(app|tests|scripts|docs|agent_tools)/[^\s]+", line.strip())
    ]
    return unique_lines(files)


def extract_traceback_files(text: str) -> list[str]:
    matches = re.findall(r'File "([^"]+\.py)"', text)
    normalized = []
    # Deeper traceback frames usually appear later and are closer to the root cause.
    for match in reversed(matches):
        path = match.strip()
        if re.match(r"^(app|tests|scripts|docs|agent_tools)/[^\s]+", path):
            normalized.append(path)
    return unique_lines(normalized)


def choose_suspected_files(
    changed_files: list[str],
    failed_tests: list[str],
    traceback_files: list[str],
) -> list[str]:
    app_changed = [path for path in changed_files if path.startswith("app/")]
    test_changed = [path for path in changed_files if path.startswith("tests/")]

    if app_changed:
        return app_changed

    if test_changed:
        return test_changed

    if traceback_files:
        return traceback_files

    return changed_files or [test.split("::", 1)[0] for test in failed_tests]


def format_list(items: list[str], default: str = "unknown") -> str:
    if not items:
        return default
    return "\n".join(items)


def format_markdown_bullets(items: list[str]) -> str:
    return "\n".join(f"- {item}" for item in items)


def build_fix_direction(suspected_files: list[str], failed_tests: list[str]) -> str:
    if suspected_files and failed_tests:
        return (
            "Review the suspected files against the failing tests. "
            "Restore the expected behavior or update the test only if the API contract intentionally changed."
        )
    if suspected_files:
        return "Review the changed files and compare them with the CI failure output."
    return "Start from the pytest output, reproduce locally, then inspect the files named in the failing tests."


def infer_patch_candidate(
    suspected_files: list[str],
    failed_tests: list[str],
    error_lines: list[str],
) -> dict[str, Any] | None:
    app_main_is_relevant = "app/main.py" in suspected_files or "tests/test_main.py::test_read_root" in failed_tests

    for line in error_lines:
        match = re.search(
            r"assert\s+\{'message':\s+'(?P<actual>[^']+)'\}\s+==\s+\{'message':\s+'(?P<expected>[^']+)'\}",
            line,
        )
        if not match:
            continue
        if not app_main_is_relevant:
            continue

        actual = match.group("actual")
        expected = match.group("expected")
        return {
            "kind": "replace_text",
            "target_file": "app/main.py",
            "find": f'return {{"message": "{actual}"}}',
            "replace": f'return {{"message": "{expected}"}}',
            "reason": "The failing test expects the previous root response value.",
            "confidence": "high",
            "safe_to_apply": True,
        }

    return None


def analyze_ci_failure(input_text: str, system_prompt: str = "", user_prompt: str = "") -> dict[str, Any]:
    failed_tests = extract_failed_tests(input_text)
    error_lines = extract_error_lines(input_text)
    changed_files = extract_changed_files(input_text)
    traceback_files = extract_traceback_files(input_text)
    suspected_files = choose_suspected_files(changed_files, failed_tests, traceback_files)
    fix_direction = build_fix_direction(suspected_files, failed_tests)
    patch_candidate = infer_patch_candidate(suspected_files, failed_tests, error_lines)
    prompt_summary = summarize_prompt(system_prompt, user_prompt)

    return {
        "prompt_context": {
            "summary": prompt_summary,
            "system_prompt_loaded": bool(system_prompt),
            "user_prompt_loaded": bool(user_prompt),
        },
        "failure_summary": "Jenkins failed during pytest.",
        "failed_tests": failed_tests,
        "error_snippet": error_lines,
        "changed_files": changed_files,
        "traceback_files": traceback_files,
        "suspected_files": suspected_files,
        "fix_direction": fix_direction,
        "patch_candidate": patch_candidate,
        "patch_draft": (
            (
                f'Apply a focused text replacement in {patch_candidate["target_file"]}: '
                f'{patch_candidate["find"]} -> {patch_candidate["replace"]}'
            )
            if patch_candidate
            else "No automatic patch was generated by this local prototype. "
            "Use the suspected files and failing tests above to make a focused fix."
        ),
        "human_review_checklist": [
            "Reproduce the failure locally.",
            "Inspect each suspected file.",
            "Confirm whether the test expectation or application behavior is the intended contract.",
            "Keep deployment disabled until CI is green again.",
        ],
        "verification": "PYTHONPATH=. pytest -q",
    }


def build_failure_report(input_text: str, system_prompt: str = "", user_prompt: str = "") -> str:
    analysis = analyze_ci_failure(input_text, system_prompt=system_prompt, user_prompt=user_prompt)

    return f"""# Debug Agent Report

## Prompt Context

```text
{analysis["prompt_context"]["summary"]}
```

## Failure Summary

{analysis["failure_summary"]}

## Failed Tests

```text
{format_list(analysis["failed_tests"])}
```

## Error Snippet

```text
{format_list(analysis["error_snippet"])}
```

## Changed Files

```text
{format_list(analysis["changed_files"])}
```

## Suspected Files

```text
{format_list(analysis["suspected_files"])}
```

## Fix Direction

{analysis["fix_direction"]}

## Patch Draft

{analysis["patch_draft"]}

## Human Review Checklist

{format_markdown_bullets(analysis["human_review_checklist"])}

## Verification

```bash
{analysis["verification"]}
```
"""


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate a CI failure report from CI artifact input.")
    parser.add_argument("--input", default="docs/debug-agent-example.md")
    parser.add_argument("--output", default="docs/debug-agent-report.md")
    parser.add_argument("--format", choices=["markdown", "json"], default="markdown")
    parser.add_argument("--system-prompt", default=str(DEFAULT_SYSTEM_PROMPT))
    parser.add_argument("--user-prompt", default=str(DEFAULT_USER_PROMPT))
    parser.add_argument("--render-prompt-output", default="")
    args = parser.parse_args()

    input_path = Path(args.input)
    output_path = Path(args.output)
    system_prompt_path = Path(args.system_prompt)
    user_prompt_path = Path(args.user_prompt)

    input_text = input_path.read_text(encoding="utf-8")
    system_prompt = read_prompt(system_prompt_path)
    user_prompt_template = read_prompt(user_prompt_path)
    rendered_user_prompt = render_user_prompt(user_prompt_template, input_text)

    if args.format == "json":
        analysis = analyze_ci_failure(input_text, system_prompt=system_prompt, user_prompt=rendered_user_prompt)
        write_json(output_path, analysis)
    else:
        report = build_failure_report(input_text, system_prompt=system_prompt, user_prompt=rendered_user_prompt)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(report, encoding="utf-8")

    if args.render_prompt_output:
        render_path = Path(args.render_prompt_output)
        render_path.parent.mkdir(parents=True, exist_ok=True)
        render_path.write_text(rendered_user_prompt, encoding="utf-8")

    print(f"Wrote {output_path}")
