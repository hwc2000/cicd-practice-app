# Debug Agent Example

## Goal

Analyze a Jenkins CI failure and suggest a safe fix.

## Inputs

- Jenkins console output
- debug-agent-input.md
- recent git diff
- pytest-output.log

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

## Pytest Output

```text
FAILED tests/test_main.py::test_read_root - AssertionError: assert {'message': 'broken'} == {'message': 'hello cicd'}
E       AssertionError: assert {'message': 'broken'} == {'message': 'hello cicd'}
```

## Expected Debug Agent Output

- Failure summary
- Failed tests
- Error snippet
- Changed files
- Suspected files
- Fix direction
- Human review checklist
- Verification commands

## Ideal Analysis

The root endpoint response changed from `hello cicd` to `broken`.
The test expects `{"message": "hello cicd"}`.
The likely fix is to restore the response in `app/main.py`.

## Verification

```bash
PYTHONPATH=. pytest -q
```
