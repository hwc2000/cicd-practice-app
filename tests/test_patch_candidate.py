import json
from pathlib import Path

import pytest

from agent_tools.patch_candidate import apply_patch_candidate, load_patch_candidate


def test_load_patch_candidate_supports_openai_report_shape():
    report = {
        "provider": "openai",
        "local_analysis": {
            "patch_candidate": {
                "kind": "replace_text",
                "target_file": "app/main.py",
                "find": 'return {"message": "broken"}',
                "replace": 'return {"message": "hello cicd"}',
                "safe_to_apply": True,
            }
        },
    }

    candidate = load_patch_candidate(report)

    assert candidate["target_file"] == "app/main.py"


def test_apply_patch_candidate_replaces_exact_text(tmp_path):
    app_dir = tmp_path / "app"
    app_dir.mkdir()
    target_file = app_dir / "main.py"
    target_file.write_text('def read_root():\n    return {"message": "broken"}\n', encoding="utf-8")

    result = apply_patch_candidate(
        {
            "kind": "replace_text",
            "target_file": "app/main.py",
            "find": 'return {"message": "broken"}',
            "replace": 'return {"message": "hello cicd"}',
            "safe_to_apply": True,
        },
        workspace=tmp_path,
        apply=True,
    )

    assert result["applied"] is True
    assert 'hello cicd' in target_file.read_text(encoding="utf-8")


def test_apply_patch_candidate_refuses_ambiguous_match(tmp_path):
    app_dir = tmp_path / "app"
    app_dir.mkdir()
    target_file = app_dir / "main.py"
    target_file.write_text(
        '\n'.join(
            [
                'return {"message": "broken"}',
                'return {"message": "broken"}',
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="multiple times"):
        apply_patch_candidate(
            {
                "kind": "replace_text",
                "target_file": "app/main.py",
                "find": 'return {"message": "broken"}',
                "replace": 'return {"message": "hello cicd"}',
                "safe_to_apply": True,
            },
            workspace=tmp_path,
            apply=True,
        )


def test_cli_output_shape_can_be_serialized(tmp_path):
    app_dir = tmp_path / "app"
    app_dir.mkdir()
    target_file = app_dir / "main.py"
    target_file.write_text('return {"message": "broken"}\n', encoding="utf-8")

    result = apply_patch_candidate(
        {
            "kind": "replace_text",
            "target_file": "app/main.py",
            "find": 'return {"message": "broken"}',
            "replace": 'return {"message": "hello cicd"}',
            "safe_to_apply": True,
        },
        workspace=tmp_path,
        apply=False,
    )

    rendered = json.dumps(result)

    assert Path(target_file).read_text(encoding="utf-8") == 'return {"message": "broken"}\n'
    assert '"applied": false' in rendered
