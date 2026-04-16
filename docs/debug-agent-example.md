# Debug Agent Example

## Goal

Analyze a Jenkins CI failure and suggest a safe fix.

## Inputs

- Jenkins console output
- debug-agent-input.md
- recent git diff
- failed test name

## Failure Summary

Test stage failed in Jenkins.

Failed test:

```text
tests/test_main.py::test_read_root
```

Error:

```text
AssertionError: assert {'message': 'broken'} == {'message': 'hello cicd'}
```

## Changed Files

```text
app/main.py
```

## Expected Debug Agent Output

- Failure summary
- Suspected files
- Root cause
- Fix direction
- Patch draft
- Verification commands

## Ideal Analysis

The root endpoint response changed from `hello cicd` to `broken`.
The test expects `{"message": "hello cicd"}`.
The likely fix is to restore the response in `app/main.py`.

## Patch Draft

```diff
-    return {"message": "broken"}
+    return {"message": "hello cicd"}
```

## Verification

```bash
PYTHONPATH=. pytest -q
```

