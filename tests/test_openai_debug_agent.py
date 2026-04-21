from types import SimpleNamespace

import pytest

from agent_tools.openai_debug_agent import (
    OpenAIDebugAgentConfig,
    build_openai_input,
    env_flag,
    extract_output_text,
    load_env_file,
    load_config,
    render_json,
    require_enabled_config,
)


def test_env_flag_accepts_common_true_values():
    assert env_flag("true") is True
    assert env_flag("1") is True
    assert env_flag("yes") is True
    assert env_flag("false") is False
    assert env_flag("") is False


def test_load_config_uses_safe_defaults():
    config = load_config({})

    assert config.api_key == ""
    assert config.model == "gpt-5.4"
    assert config.timeout_seconds == 30.0
    assert config.enabled is False


def test_load_env_file_reads_simple_key_values(tmp_path):
    env_file = tmp_path / ".env"
    env_file.write_text(
        """
# comment
OPENAI_API_KEY='secret'
OPENAI_MODEL="gpt-5.4"
OPENAI_DEBUG_AGENT_ENABLED=true
""".strip(),
        encoding="utf-8",
    )

    values = load_env_file(env_file)

    assert values["OPENAI_API_KEY"] == "secret"
    assert values["OPENAI_MODEL"] == "gpt-5.4"
    assert values["OPENAI_DEBUG_AGENT_ENABLED"] == "true"


def test_require_enabled_config_blocks_accidental_calls():
    with pytest.raises(RuntimeError, match="OPENAI_DEBUG_AGENT_ENABLED"):
        require_enabled_config(OpenAIDebugAgentConfig(api_key="secret", enabled=False))

    with pytest.raises(RuntimeError, match="OPENAI_API_KEY"):
        require_enabled_config(OpenAIDebugAgentConfig(api_key="", enabled=True))


def test_build_openai_input_includes_local_analysis():
    messages = build_openai_input(
        debug_input="raw ci log",
        system_prompt="system",
        rendered_user_prompt="user prompt",
        analysis={"failed_tests": ["tests/test_main.py::test_read_root"]},
    )

    assert messages[0]["role"] == "developer"
    assert messages[1]["role"] == "user"
    assert "Deterministic Local Analysis" in messages[1]["content"]
    assert "tests/test_main.py::test_read_root" in messages[1]["content"]


def test_extract_output_text_supports_response_output_shape():
    response = SimpleNamespace(
        output=[
            SimpleNamespace(
                content=[
                    SimpleNamespace(text="first"),
                    SimpleNamespace(text="second"),
                ]
            )
        ]
    )

    assert extract_output_text(response) == "first\nsecond"


def test_render_json_escapes_non_ascii_text():
    rendered = render_json(
        {
            "provider": "openai",
            "output_text": "요약",
            "local_analysis": {"note": "한글"},
        }
    )

    assert "\\uc694\\uc57d" in rendered
    assert "\\ud55c\\uae00" in rendered
    assert "요약" not in rendered
