"""Optional OpenAI-backed Debug Agent interface.

This module keeps the LLM boundary thin on purpose. The local rule-based
analyzer and graph runners still produce deterministic state; this layer only
turns that state plus the prompt templates into an OpenAI Responses API call.
"""

from __future__ import annotations

import argparse
import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

from agent_tools.debug_agent import (
    DEFAULT_SYSTEM_PROMPT,
    DEFAULT_USER_PROMPT,
    analyze_failure,
    read_prompt,
    render_user_prompt,
)


DEFAULT_MODEL = "gpt-5.4"


class ResponsesClient(Protocol):
    def create(self, **kwargs: Any) -> Any:
        """Create a model response."""


@dataclass(frozen=True)
class OpenAIDebugAgentConfig:
    api_key: str
    model: str = DEFAULT_MODEL
    timeout_seconds: float = 30.0
    enabled: bool = False


def env_flag(value: str | None) -> bool:
    return (value or "").strip().lower() in {"1", "true", "yes", "on"}


def load_env_file(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}

    values: dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key:
            values[key] = value
    return values


def merged_env(env_file: Path) -> dict[str, str]:
    values = dict(os.environ)
    for key, value in load_env_file(env_file).items():
        values.setdefault(key, value)
    return values


def load_config(env: dict[str, str] | None = None) -> OpenAIDebugAgentConfig:
    source = env if env is not None else os.environ
    timeout_raw = source.get("OPENAI_TIMEOUT_SECONDS", "30")
    try:
        timeout_seconds = float(timeout_raw)
    except ValueError:
        timeout_seconds = 30.0

    return OpenAIDebugAgentConfig(
        api_key=source.get("OPENAI_API_KEY", ""),
        model=source.get("OPENAI_MODEL", DEFAULT_MODEL),
        timeout_seconds=timeout_seconds,
        enabled=env_flag(source.get("OPENAI_DEBUG_AGENT_ENABLED")),
    )


def require_enabled_config(config: OpenAIDebugAgentConfig) -> None:
    if not config.enabled:
        raise RuntimeError("Set OPENAI_DEBUG_AGENT_ENABLED=true before calling OpenAI.")
    if not config.api_key:
        raise RuntimeError("Set OPENAI_API_KEY before calling OpenAI.")


def build_openai_input(
    debug_input: str,
    system_prompt: str,
    rendered_user_prompt: str,
    analysis: dict[str, Any],
) -> list[dict[str, str]]:
    """Build the Responses API input items.

    Keeping this as a pure function gives us a clean harness target before any
    network calls are involved.
    """
    analysis_json = json.dumps(analysis, ensure_ascii=False, indent=2)
    return [
        {
            "role": "developer",
            "content": system_prompt.strip()
            or "너는 CI 실패 분석 도우미다. 짧게 답하고 위험한 변경 전에는 사람 리뷰를 요구한다.",
        },
        {
            "role": "user",
            "content": (
                f"{rendered_user_prompt.strip()}\n\n"
                "## Deterministic Local Analysis\n"
                "이 구조화 분석을 1차 근거로 사용해. 파일명이나 테스트명을 지어내지 마.\n\n"
                f"```json\n{analysis_json}\n```\n\n"
                "짧은 한국어 markdown 리포트를 작성해. 항목은 요약, 가능성 높은 원인, 다음 수정, 검증으로 나눠줘."
            ),
        },
    ]


def extract_output_text(response: Any) -> str:
    output_text = getattr(response, "output_text", None)
    if output_text:
        return str(output_text)

    output = getattr(response, "output", None) or []
    chunks: list[str] = []
    for item in output:
        for content in getattr(item, "content", []) or []:
            text = getattr(content, "text", None)
            if text:
                chunks.append(str(text))
    return "\n".join(chunks).strip()


def create_openai_client(config: OpenAIDebugAgentConfig) -> ResponsesClient:
    try:
        from openai import OpenAI
    except ImportError as exc:
        raise RuntimeError("Install the openai package before calling OpenAI.") from exc

    client = OpenAI(api_key=config.api_key, timeout=config.timeout_seconds)
    return client.responses


def run_openai_debug_agent(
    debug_input: str,
    system_prompt: str,
    rendered_user_prompt: str,
    config: OpenAIDebugAgentConfig,
    responses_client: ResponsesClient | None = None,
) -> dict[str, Any]:
    require_enabled_config(config)
    analysis = analyze_failure(
        debug_input,
        system_prompt=system_prompt,
        user_prompt=rendered_user_prompt,
    )
    openai_input = build_openai_input(debug_input, system_prompt, rendered_user_prompt, analysis)
    client = responses_client or create_openai_client(config)
    response = client.create(
        model=config.model,
        input=openai_input,
    )

    return {
        "provider": "openai",
        "model": config.model,
        "response_id": getattr(response, "id", ""),
        "output_text": extract_output_text(response),
        "local_analysis": analysis,
    }


def render_markdown(result: dict[str, Any]) -> str:
    return f"""# OpenAI Debug Agent 리포트

## Provider

```text
{result["provider"]} / {result["model"]}
```

## Response ID

```text
{result.get("response_id") or "unknown"}
```

## Report

{result.get("output_text") or "No output text was returned."}
"""


def render_json(result: dict[str, Any]) -> str:
    """Render JSON with ASCII escapes to avoid artifact viewer encoding issues."""
    return json.dumps(result, ensure_ascii=True, indent=2) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the optional OpenAI-backed Debug Agent.")
    parser.add_argument("--input", default="docs/debug-agent-example.md")
    parser.add_argument("--output", default="debug-openai-report.md")
    parser.add_argument("--format", choices=["markdown", "json"], default="markdown")
    parser.add_argument("--system-prompt", default=str(DEFAULT_SYSTEM_PROMPT))
    parser.add_argument("--user-prompt", default=str(DEFAULT_USER_PROMPT))
    parser.add_argument("--env-file", default=".env")
    args = parser.parse_args()

    input_text = Path(args.input).read_text(encoding="utf-8")
    system_prompt = read_prompt(Path(args.system_prompt))
    user_prompt_template = read_prompt(Path(args.user_prompt))
    rendered_user_prompt = render_user_prompt(user_prompt_template, input_text)
    try:
        result = run_openai_debug_agent(
            debug_input=input_text,
            system_prompt=system_prompt,
            rendered_user_prompt=rendered_user_prompt,
            config=load_config(merged_env(Path(args.env_file))),
        )
    except RuntimeError as exc:
        raise SystemExit(f"OpenAI Debug Agent skipped: {exc}") from exc

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if args.format == "json":
        output_path.write_text(render_json(result), encoding="utf-8")
    else:
        output_path.write_text(render_markdown(result), encoding="utf-8")

    print(f"Wrote {output_path}")


if __name__ == "__main__":
    main()
