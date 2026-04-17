from agent_tools.compare_graph_states import compare_states


def test_compare_states_matches_equivalent_core_fields():
    local = {
        "analysis": {
            "failed_tests": ["tests/test_main.py::test_read_root"],
            "error_snippet": ["AssertionError: x"],
            "changed_files": ["app/main.py"],
            "suspected_files": ["app/main.py"],
            "fix_direction": "Review the suspected files.",
        },
        "decision": "manual_review_required",
        "needs_human_review": True,
    }
    langgraph = {
        "analysis": {
            "failed_tests": ["tests/test_main.py::test_read_root"],
            "error_snippet": ["AssertionError: x"],
            "changed_files": ["app/main.py"],
            "suspected_files": ["app/main.py"],
            "fix_direction": "Review the suspected files.",
        },
        "decision": "manual_review_required",
        "needs_human_review": True,
    }

    result = compare_states(local, langgraph)

    assert result["matched"] is True
    assert result["differences"] == []


def test_compare_states_reports_differences():
    local = {
        "analysis": {
            "failed_tests": ["tests/test_main.py::test_read_root"],
            "error_snippet": ["AssertionError: x"],
            "changed_files": ["app/main.py"],
            "suspected_files": ["app/main.py"],
            "fix_direction": "Review the suspected files.",
        },
        "decision": "manual_review_required",
        "needs_human_review": True,
    }
    langgraph = {
        "analysis": {
            "failed_tests": ["tests/test_main.py::test_health_check"],
            "error_snippet": ["AssertionError: x"],
            "changed_files": ["app/main.py"],
            "suspected_files": ["app/main.py"],
            "fix_direction": "Review the suspected files.",
        },
        "decision": "manual_review_required",
        "needs_human_review": True,
    }

    result = compare_states(local, langgraph)

    assert result["matched"] is False
    assert result["differences"] == [
        {
            "key": "analysis.failed_tests",
            "local": ["tests/test_main.py::test_read_root"],
            "langgraph": ["tests/test_main.py::test_health_check"],
        }
    ]

