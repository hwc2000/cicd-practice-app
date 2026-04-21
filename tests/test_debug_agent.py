from agent_tools.debug_agent import analyze_failure, build_report


CI_FAILURE_INPUT = """# Debug Agent Input

## Changed Files
app/main.py
tests/test_main.py

## Pytest Output
FAILED tests/test_main.py::test_read_root - AssertionError: assert {'message': 'broken'} == {'message': 'hello cicd'}
E       AssertionError: assert {'message': 'broken'} == {'message': 'hello cicd'}
"""


def test_analyze_failure_extracts_pytest_failure_details():
    analysis = analyze_failure(
        CI_FAILURE_INPUT,
        system_prompt="system prompt",
        user_prompt="user prompt",
    )

    assert analysis["failed_tests"] == ["tests/test_main.py::test_read_root"]
    assert analysis["error_snippet"] == [
        "AssertionError: assert {'message': 'broken'} == {'message': 'hello cicd'}"
    ]
    assert analysis["changed_files"] == ["app/main.py", "tests/test_main.py"]
    assert analysis["suspected_files"] == ["app/main.py"]
    assert analysis["patch_candidate"] == {
        "kind": "replace_text",
        "target_file": "app/main.py",
        "find": 'return {"message": "broken"}',
        "replace": 'return {"message": "hello cicd"}',
        "reason": "The failing test expects the previous root response value.",
        "confidence": "high",
        "safe_to_apply": True,
    }
    assert 'return {"message": "broken"} -> return {"message": "hello cicd"}' in analysis["patch_draft"]
    assert analysis["prompt_context"]["system_prompt_loaded"] is True
    assert analysis["prompt_context"]["user_prompt_loaded"] is True


def test_build_report_renders_human_review_sections():
    report = build_report(CI_FAILURE_INPUT)

    assert "# Debug Agent Report" in report
    assert "tests/test_main.py::test_read_root" in report
    assert "app/main.py" in report
    assert "manual" not in report.lower()
    assert "PYTHONPATH=. pytest -q" in report


def test_analyze_failure_returns_no_patch_candidate_for_unknown_pattern():
    analysis = analyze_failure(
        """# Debug Agent Input

## Changed Files
scripts/deploy.sh

## Pytest Output
FAILED tests/test_main.py::test_read_root - RuntimeError: boom
E       RuntimeError: boom
""",
    )

    assert analysis["patch_candidate"] is None
