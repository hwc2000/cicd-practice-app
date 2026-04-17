import sys
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from run_debug_graph import public_state, run_graph


def test_run_graph_returns_manual_review_state(tmp_path):
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

    state = run_graph(
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


def test_public_state_hides_full_prompt_and_report():
    state = {
        "input_path": "debug-agent-input.md",
        "system_prompt_path": "system.md",
        "user_prompt_path": "user.md",
        "analysis": {"failed_tests": []},
        "decision": "manual_review_required",
        "needs_human_review": True,
        "rendered_user_prompt": "x" * 600,
        "report_markdown": "y" * 600,
    }

    result = public_state(state)

    assert len(result["rendered_user_prompt_preview"]) == 500
    assert len(result["report_markdown_preview"]) == 500
    assert result["decision"] == "manual_review_required"

