#!/usr/bin/env python3
"""Create a first-pass debug report from a CI failure note."""

from __future__ import annotations

import argparse
import re
from pathlib import Path


def extract_first(pattern: str, text: str, default: str = "unknown") -> str:
    match = re.search(pattern, text, re.MULTILINE)
    if not match:
        return default
    return (match.group(1) if match.groups() else match.group(0)).strip()


def build_report(input_text: str) -> str:
    failed_test = extract_first(r"^(?:FAILED\s+)?(tests/.+::\w+)", input_text)
    changed_file = extract_first(r"^app/.+", input_text)
    assertion = extract_first(r"^E\s+(AssertionError:.+)$", input_text)
    if assertion == "unknown":
        assertion = extract_first(r"^(AssertionError:.+)$", input_text)

    return f"""# Debug Agent Report

## Failure Summary

Jenkins failed during the test stage.

Failed test:

```text
{failed_test}
```

Error:

```text
{assertion}
```

## Suspected Files

```text
{changed_file}
```

## Root Cause

The root endpoint response no longer matches the expected API contract in the test.

## Fix Direction

Restore the root endpoint response so it matches `tests/test_main.py`.

## Patch Draft

```diff
-    return {{"message": "broken"}}
+    return {{"message": "hello cicd"}}
```

## Verification

```bash
PYTHONPATH=. pytest -q
```
"""


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate a debug report from CI failure input.")
    parser.add_argument("--input", default="docs/debug-agent-example.md")
    parser.add_argument("--output", default="docs/debug-agent-report.md")
    args = parser.parse_args()

    input_path = Path(args.input)
    output_path = Path(args.output)

    input_text = input_path.read_text(encoding="utf-8")
    report = build_report(input_text)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(report, encoding="utf-8")
    print(f"Wrote {output_path}")


if __name__ == "__main__":
    main()
