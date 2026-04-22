# Auto-Fix Agent User Prompt

아래 CI 실패를 분석하고 코드 수정안을 생성해줘.

입력:

```text
{{DEBUG_AGENT_INPUT}}
```

출력은 한국어 markdown으로 작성하되, 마지막에 아래 형태의 JSON 코드 블록을 반드시 포함해줘:

```json
{
  "kind": "replace_text",
  "target_file": "수정할 파일 경로",
  "find": "현재 코드에서 찾을 정확한 문자열",
  "replace": "대체할 문자열",
  "reason": "이 수정이 필요한 이유",
  "confidence": "high 또는 low",
  "safe_to_apply": true
}
```

포함할 내용:

- 실패 요약
- 가능성 높은 원인
- 수정안 (위 JSON 형태)
- 검증 명령어
