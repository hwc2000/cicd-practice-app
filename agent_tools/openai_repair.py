"""OpenAI-backed repair/report helpers for CI failure workflows."""

from __future__ import annotations

import argparse
import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

from agent_tools.failure_context import (
    DEFAULT_SYSTEM_PROMPT,
    DEFAULT_USER_PROMPT,
    analyze_ci_failure,
    read_prompt,
    render_user_prompt,
)


DEFAULT_MODEL = "gpt-5.4"


class ResponsesClient(Protocol):
    def create(self, **kwargs: Any) -> Any:
        """Create a model response."""


@dataclass(frozen=True)
class OpenAIRepairConfig:
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


def load_config(env: dict[str, str] | None = None) -> OpenAIRepairConfig:
    source = env if env is not None else os.environ
    timeout_raw = source.get("OPENAI_TIMEOUT_SECONDS", "30")
    try:
        timeout_seconds = float(timeout_raw)
    except ValueError:
        timeout_seconds = 30.0

    return OpenAIRepairConfig(
        api_key=source.get("OPENAI_API_KEY", ""),
        model=source.get("OPENAI_MODEL", DEFAULT_MODEL),
        timeout_seconds=timeout_seconds,
        enabled=env_flag(source.get("OPENAI_DEBUG_AGENT_ENABLED")),
    )


def require_enabled_config(config: OpenAIRepairConfig) -> None:
    if not config.enabled:
        raise RuntimeError("Set OPENAI_DEBUG_AGENT_ENABLED=true before calling OpenAI.")
    if not config.api_key:
        raise RuntimeError("Set OPENAI_API_KEY before calling OpenAI.")


def build_repair_messages(
    debug_input: str,
    system_prompt: str,
    rendered_user_prompt: str,
    analysis: dict[str, Any],
) -> list[dict[str, str]]:
    analysis_json = json.dumps(analysis, ensure_ascii=False, indent=2)
    return [
        {
            "role": "developer",
            "content": system_prompt.strip()
            or "너는 CI 실패 복구 도우미다. 짧게 답하고 위험한 변경 전에는 사람 리뷰를 요구한다.",
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


def create_openai_client(config: OpenAIRepairConfig) -> ResponsesClient:
    try:
        from openai import OpenAI
    except ImportError as exc:
        raise RuntimeError("Install the openai package before calling OpenAI.") from exc

    client = OpenAI(api_key=config.api_key, timeout=config.timeout_seconds)
    return client.responses


def run_openai_repair_report(
    debug_input: str,
    system_prompt: str,
    rendered_user_prompt: str,
    config: OpenAIRepairConfig,
    responses_client: ResponsesClient | None = None,
) -> dict[str, Any]:
    require_enabled_config(config)
    analysis = analyze_ci_failure(
        debug_input,
        system_prompt=system_prompt,
        user_prompt=rendered_user_prompt,
    )
    messages = build_repair_messages(debug_input, system_prompt, rendered_user_prompt, analysis)
    client = responses_client or create_openai_client(config)
    response = client.create(model=config.model, input=messages)

    return {
        "provider": "openai",
        "model": config.model,
        "response_id": getattr(response, "id", ""),
        "output_text": extract_output_text(response),
        "local_analysis": analysis,
    }


def generate_openai_patch(
    ci_input: str,
    suspected_files: dict[str, str],
    analysis: dict[str, Any],
    config: OpenAIRepairConfig,
    responses_client: ResponsesClient | None = None,
) -> dict[str, Any] | None:
    require_enabled_config(config)

    system_prompt = (
        "너는 CI 자동 수정 에이전트다.\n\n"
        "규칙:\n"
        "- 한 번에 하나의 파일만 수정한다.\n"
        "- 하지만 가장 먼저 실패를 멈추게 하는 root cause 파일을 우선 선택한다.\n"
        "- 같은 로그에 여러 오류가 보이면, 테스트 기대값보다 런타임 예외(NameError, ImportError, TypeError 등)를 먼저 해결한다.\n"
        "- retry 시 이전 패치가 workspace에 남아 있을 수 있으므로 현재 제공된 소스코드를 기준으로 다음 수정 대상을 다시 판단한다.\n"
        "- 수정은 반드시 replace_text JSON 형태로 구조화한다.\n"
        "- find 문자열은 소스코드에서 정확히 존재하는 부분을 복사한다.\n"
        "- 테스트 코드를 바꿔서 통과시키는 것은 금지한다.\n"
        "- 불확실하면 confidence를 low로 표시한다.\n"
        "- JSON 코드 블록을 반드시 하나만 출력한다."
    )

    files_section = ""
    for filepath, content in suspected_files.items():
        files_section += f"\n### {filepath}\n```python\n{content}\n```\n"

    analysis_json = json.dumps(analysis, ensure_ascii=False, indent=2)

    user_prompt = (
        "CI 실패를 분석하고 코드 수정안을 생성해줘.\n\n"
        "## 실패 정보\n"
        f"```text\n{ci_input[:4000]}\n```\n\n"
        "## Failure Context\n"
        f"```json\n{analysis_json}\n```\n\n"
        "## 의심 파일 소스코드\n"
        f"{files_section}\n"
        "## 출력 형식\n"
        "반드시 아래 형태의 JSON 코드 블록 하나를 포함해줘:\n\n"
        "```json\n"
        "{\n"
        '  "kind": "replace_text",\n'
        '  "target_file": "수정할 파일 경로",\n'
        '  "find": "현재 코드에서 찾을 정확한 문자열",\n'
        '  "replace": "대체할 문자열",\n'
        '  "reason": "이 수정이 필요한 이유",\n'
        '  "confidence": "high 또는 low",\n'
        '  "safe_to_apply": true\n'
        "}\n"
        "```\n\n"
        "중요: find 문자열은 소스코드에 실제로 존재해야 한다. "
        "테스트 파일을 수정하지 않는다. "
        "여러 실패가 보이면 가장 먼저 테스트 실행을 막는 런타임 예외를 일으키는 파일을 선택하라."
    )

    client = responses_client or create_openai_client(config)
    response = client.create(
        model=config.model,
        input=[
            {"role": "developer", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
    )
    return _extract_patch_json(extract_output_text(response))


def _extract_patch_json(text: str) -> dict[str, Any] | None:
    import re

    json_blocks = re.findall(r"```json\s*\n(.*?)\n```", text, re.DOTALL)
    for block in json_blocks:
        try:
            data = json.loads(block)
            if isinstance(data, dict) and data.get("kind") == "replace_text":
                return data
        except json.JSONDecodeError:
            continue
    return None


def render_markdown(result: dict[str, Any]) -> str:
    return f"""# OpenAI Repair Report

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
    return json.dumps(result, ensure_ascii=True, indent=2) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the optional OpenAI-backed CI repair report.")
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
        result = run_openai_repair_report(
            debug_input=input_text,
            system_prompt=system_prompt,
            rendered_user_prompt=rendered_user_prompt,
            config=load_config(merged_env(Path(args.env_file))),
        )
    except RuntimeError as exc:
        raise SystemExit(f"OpenAI repair report skipped: {exc}") from exc

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if args.format == "json":
        output_path.write_text(render_json(result), encoding="utf-8")
    else:
        output_path.write_text(render_markdown(result), encoding="utf-8")

    print(f"Wrote {output_path}")
