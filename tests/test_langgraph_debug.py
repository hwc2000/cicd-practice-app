import pytest


pytest.importorskip("langgraph")

from agent_tools.langgraph_debug import run_langgraph


def test_run_langgraph_returns_manual_review_state(tmp_path):
    input_path = tmp_path / "debug-agent-input.md"
    system_prompt_path = tmp_path / "system.md"
    user_prompt_path = tmp_path / "user.md"

    input_path.write_text(
        """# Debug Agent Input

## Changed Files
app/main.py

## Pytest Output
FAILED tests/test_main.py::test_read_root - AssertionError: assert {'message': 'broken'} == {'message': 'hello cicd'}
""",
        encoding="utf-8",
    )
    system_prompt_path.write_text("You are a cautious CI Debug Agent.", encoding="utf-8")
    user_prompt_path.write_text("Analyze:\n{{DEBUG_AGENT_INPUT}}", encoding="utf-8")

    state = run_langgraph(
        {
            "input_path": str(input_path),
            "system_prompt_path": str(system_prompt_path),
            "user_prompt_path": str(user_prompt_path),
        }
    )

    assert state["analysis"]["failed_tests"] == ["tests/test_main.py::test_read_root"]
    assert state["analysis"]["suspected_files"] == ["app/main.py"]
    assert state["decision"] == "manual_review_required"
    assert state["needs_human_review"] is True
    assert "Debug Agent Report" in state["report_markdown"]

