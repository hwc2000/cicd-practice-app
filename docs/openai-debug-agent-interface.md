# OpenAI Debug Agent Interface

이 문서는 CI 실패 분석기에 OpenAI API를 붙이는 경계를 정리합니다.

## Goal

현재 Debug Agent는 세 층으로 나눕니다.

```text
Jenkins failure artifact
-> deterministic parser/tool
-> local graph 또는 LangGraph state
-> optional OpenAI report
```

OpenAI 호출은 선택 기능입니다. 기본 Jenkins 빌드, pytest, Docker build는 API key 없이 계속 동작해야 합니다.

## Environment

`.env.example`을 기준으로 로컬 환경변수를 준비합니다.

```bash
cp .env.example .env
vim .env
```

`OPENAI_DEBUG_AGENT_ENABLED=true`를 요구하는 이유는 실수로 CI에서 API 비용이 발생하는 것을 막기 위해서입니다.

## Input Contract

OpenAI layer는 아래 입력만 받습니다.

```text
debug-agent-input.md
prompts/debug-agent-system.md
prompts/debug-agent-user.md
deterministic local analysis JSON
```

LLM은 git checkout, 파일 수정, 배포 실행 권한을 갖지 않습니다. 현재 단계에서는 리포트만 생성합니다.

## Output Contract

기본 출력은 markdown입니다.

```text
debug-openai-report.md
```

JSON 출력도 가능합니다.

```bash
python3 scripts/run_openai_debug_agent.py \
  --input debug-agent-input.md \
  --output debug-openai-report.json \
  --format json
```

JSON 필드는 아래 형태를 유지합니다.

```json
{
  "provider": "openai",
  "model": "gpt-5.4",
  "response_id": "resp_...",
  "output_text": "...",
  "local_analysis": {}
}
```

## CLI

로컬에서 수동 실행합니다.

```bash
python3 scripts/run_openai_debug_agent.py \
  --input docs/debug-agent-example.md \
  --output docs/openai-debug-agent-report.md \
  --env-file .env
```

Jenkins에 바로 연결하지 않습니다. 먼저 로컬에서 API 응답 품질과 비용을 확인한 뒤, 실패 post artifact에 추가할지 결정합니다.

## Future Tool Boundary

나중에 harness/tool 공부로 넘어가면 아래 함수들이 우선 연결 지점입니다.

```text
agent_tools.openai_debug_agent.build_openai_input
agent_tools.openai_debug_agent.run_openai_debug_agent
agent_tools.debug_agent.analyze_failure
agent_tools.debug_graph.run_graph
agent_tools.langgraph_debug.run_langgraph
```

우선순위는 아래 순서입니다.

```text
1. parser/tool 결과를 신뢰 가능한 구조로 만든다.
2. graph state를 비교 가능하게 유지한다.
3. LLM은 그 구조를 읽고 설명/판단 품질을 높인다.
4. 자동 수정/자동 배포는 별도 human approval 전까지 금지한다.
```
