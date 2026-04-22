"""Compatibility wrapper for the legacy OpenAI Debug Agent module.

Import from ``agent_tools.openai_repair`` for new code.
"""

from agent_tools.openai_repair import (  # noqa: F401
    DEFAULT_MODEL,
    OpenAIRepairConfig,
    build_repair_messages,
    create_openai_client,
    env_flag,
    extract_output_text,
    generate_openai_patch,
    load_config,
    load_env_file,
    main,
    merged_env,
    render_json,
    render_markdown,
    require_enabled_config,
    run_openai_repair_report,
)


OpenAIDebugAgentConfig = OpenAIRepairConfig
build_openai_input = build_repair_messages
run_openai_debug_agent = run_openai_repair_report
