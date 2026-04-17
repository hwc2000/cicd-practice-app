# Debug Agent Tool Contract

This project keeps the Debug Agent usable in two ways:

1. CLI tool for Jenkins or shell scripts
2. Importable Python function for a future harness

## CLI Usage

Markdown report:

```bash
python3 scripts/debug_agent.py \
  --input debug-agent-input.md \
  --output debug-agent-report.md
```

JSON report:

```bash
python3 scripts/debug_agent.py \
  --input debug-agent-input.md \
  --output debug-agent-report.json \
  --format json
```

Rendered prompt preview:

```bash
python3 scripts/debug_agent.py \
  --input debug-agent-input.md \
  --output debug-agent-report.md \
  --render-prompt-output debug-agent-rendered-user-prompt.md
```

## Python Usage

```python
from agent_tools.debug_agent import analyze_failure

analysis = analyze_failure(input_text, system_prompt=system_prompt, user_prompt=user_prompt)
```

The function returns a dictionary with these keys:

```text
prompt_context
failure_summary
failed_tests
error_snippet
changed_files
suspected_files
fix_direction
patch_draft
human_review_checklist
verification
```

## Tool Boundary

The Debug Agent is read-only by design.

It may:

- Read CI failure input
- Read prompt templates
- Produce Markdown or JSON reports
- Render the user prompt that would be sent to an LLM

It must not:

- Deploy
- Merge
- Push commits
- Modify application source files automatically
- Hide uncertainty when CI input is incomplete
