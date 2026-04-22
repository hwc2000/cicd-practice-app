# Debug Agent Input

## Build
- Job: cicd-practice-app
- Build number: 49
- Branch: unknown
- Commit: 9be1b7c42af4ee700ee2d03d6fb4338e25f1b73c

## Recent Commit
9be1b7c Add auto-fix loop: autofix_graph, run_autofix, updated Jenkinsfile with AUTOFIX_ENABLED param

## Changed Files
Jenkinsfile
agent_tools/autofix_graph.py
docs/debug-openai-report.json
prompts/autofix-system.md
prompts/autofix-user.md
scripts/run_autofix.py
tests/test_autofix_graph.py

## Recent Diff
 Jenkinsfile                   | 154 +++++++++------------
 agent_tools/autofix_graph.py  | 310 ++++++++++++++++++++++++++++++++++++++++++
 docs/debug-openai-report.json |  35 +++++
 prompts/autofix-system.md     |  19 +++
 prompts/autofix-user.md       |  30 ++++
 scripts/run_autofix.py        |  62 +++++++++
 tests/test_autofix_graph.py   | 239 ++++++++++++++++++++++++++++++++
 7 files changed, 759 insertions(+), 90 deletions(-)

## Pytest Output
..................F..............                                        [100%]
=================================== FAILURES ===================================
________________________________ test_read_root ________________________________

    def test_read_root():
        response = client.get("/")
    
        assert response.status_code == 200
>       assert response.json() == {"message": "hello cicd"}
E       AssertionError: assert {'message': 'broken'} == {'message': 'hello cicd'}
E         
E         Differing items:
E         {'message': 'broken'} != {'message': 'hello cicd'}
E         
E         Full diff:
E           {
E         -     'message': 'hello cicd',
E         +     'message': 'broken',
E           }

tests/test_main.py:13: AssertionError
=========================== short test summary info ============================
FAILED tests/test_main.py::test_read_root - AssertionError: assert {'message': 'broken'} == {'message': 'hello cicd'}
  
  Differing items:
  {'message': 'broken'} != {'message': 'hello cicd'}
  
  Full diff:
    {
  -     'message': 'hello cicd',
  +     'message': 'broken',
    }
1 failed, 32 passed in 4.10s
