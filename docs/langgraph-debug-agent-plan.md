# LangGraph Debug Agent Plan

This document sketches how the current Debug Agent tool can become a LangGraph workflow later.

The goal is not to add LangGraph immediately. The goal is to keep today's CI artifact work compatible with a future graph-based agent.

## Current Building Blocks

```text
Jenkins failure
-> debug-agent-input.md
-> pytest-output.log
-> scripts/debug_agent.py
-> debug-agent-report.md
-> optional JSON analysis
```

The current script already has a tool-like boundary:

```text
analyze_failure(input_text, system_prompt, user_prompt) -> dict
```

That function can become either:

- a LangGraph node
- a tool called by a LangGraph node
- a baseline parser before an LLM node

## Proposed Graph State

```python
class DebugAgentState(TypedDict, total=False):
    ci_input: str
    pytest_output: str
    system_prompt: str
    user_prompt_template: str
    rendered_user_prompt: str
    analysis: dict
    report_markdown: str
    decision: str
    needs_human_review: bool
```

## Proposed Nodes

```text
load_artifacts
-> render_prompt
-> analyze_failure_tool
-> render_report
-> require_human_review
```

### load_artifacts

Reads Jenkins artifacts from local files or downloaded build artifacts.

Inputs:

```text
debug-agent-input.md
pytest-output.log
prompt templates
```

Outputs:

```text
ci_input
pytest_output
system_prompt
user_prompt_template
```

### render_prompt

Combines the user prompt template with CI input.

Output:

```text
rendered_user_prompt
```

### analyze_failure_tool

Calls the current read-only tool function.

```python
analysis = analyze_failure(
    input_text=state["ci_input"],
    system_prompt=state["system_prompt"],
    user_prompt=state["rendered_user_prompt"],
)
```

Output:

```text
analysis
```

### render_report

Renders Markdown or JSON output from the structured analysis.

Output:

```text
report_markdown
```

### require_human_review

Stops the graph with a human review decision. This is intentionally conservative.

Output:

```text
needs_human_review = True
decision = "manual_review_required"
```

## Future LLM Node

Later, an LLM node can be inserted after the rule-based parser:

```text
analyze_failure_tool
-> llm_debug_hypothesis
-> render_report
```

The LLM node should receive:

```text
system prompt
rendered user prompt
structured parser output
```

It should return:

```text
root cause hypotheses
safe fix direction
verification plan
questions for human review
```

It should not return:

```text
deployment commands
automatic merge commands
destructive shell commands
```

## Tool And Graph Boundary

The graph orchestrates steps.

The tool analyzes CI input.

```text
Graph:
sequence, branching, state, human stop points

Tool:
parse failure input, extract facts, produce structured analysis
```

Keeping these separate makes the project easier to test:

- Unit test the tool with plain strings.
- Integration test the graph with small fixture files.
- Jenkins can keep using the CLI until the graph is ready.

## Recommended Next Prototype

Do not connect Jenkins directly to LangGraph yet.

First prototype a local graph runner:

```text
scripts/run_debug_graph.py
```

It should:

1. Read `docs/debug-agent-example.md`
2. Load prompt templates
3. Call the current `analyze_failure` function
4. Print the graph state as JSON

Only after that works should Jenkins call the graph runner.

## Local Runner Command

```bash
python3 scripts/run_debug_graph.py \
  --input docs/debug-agent-example.md \
  --output /tmp/debug-graph-state.json
```

This runner does not import LangGraph yet. It keeps the same node shape so the functions can later move into a real `StateGraph`.
