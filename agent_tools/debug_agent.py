"""Compatibility wrapper for the legacy Debug Agent module.

The project is moving toward reusable CI failure-context + repair services.
Import from ``agent_tools.failure_context`` for new code.
"""

from agent_tools.failure_context import (  # noqa: F401
    DEFAULT_SYSTEM_PROMPT,
    DEFAULT_USER_PROMPT,
    build_failure_report,
    choose_suspected_files,
    extract_changed_files,
    extract_error_lines,
    extract_failed_tests,
    extract_section,
    format_list,
    format_markdown_bullets,
    infer_patch_candidate,
    main,
    read_prompt,
    render_user_prompt,
    summarize_prompt,
    unique_lines,
    write_json,
)
from agent_tools.failure_context import analyze_ci_failure as analyze_failure


def build_report(input_text: str, system_prompt: str = "", user_prompt: str = "") -> str:
    report = build_failure_report(input_text, system_prompt=system_prompt, user_prompt=user_prompt)
    return report.replace("# CI Failure Report", "# Debug Agent Report", 1)
