# cicd-practice-app

FastAPI 기반 CI/CD 실습 앱입니다. 이 저장소의 목적은 Jenkins 자체를 깊게 학습하는 것이 아니라, 나중에 만들 Debug Agent / CI-CD Agent가 읽을 수 있는 실제 CI 실패 로그와 git diff를 만들어보는 것입니다.

## Current Status

2026-04-17 기준으로 아래까지 완료했습니다.

```text
1. GitHub repo push 완료
2. VirtualBox에 jenkins-server VM 생성
3. Ubuntu Server 설치
4. Jenkins 설치 및 초기 설정
5. Docker 설치
6. jenkins 사용자의 Docker 실행 권한 설정
7. Jenkins Pipeline job 생성
8. Pipeline script from SCM으로 GitHub repo 연결
9. 수동 빌드 성공
10. pytest 통과
11. Docker image build 성공
12. Deploy stage는 RUN_DEPLOY=false 조건으로 skip
13. 의도적 테스트 실패 생성 및 Jenkins 실패 로그 확인
14. 실패 원인 수정 후 Jenkins SUCCESS 재확인
15. Debug Agent 입력 예시 문서 추가
16. 초기 Debug Agent 목업 스크립트 추가
17. Jenkins 실패 시 Debug Agent 리포트 artifact 자동 생성 연결
18. pytest 실패 출력을 pytest-output.log artifact로 저장하도록 연결
19. Debug Agent 목업 스크립트를 pytest 로그 기반 일반형 리포트로 개선
20. Debug Agent system/user prompt 템플릿 분리
21. Debug Agent를 harness/tool 호출에 대비해 JSON 출력과 함수형 API로 정리
22. LangGraph 전환 계획 문서 추가
23. LangGraph 스타일 로컬 graph runner prototype 추가
24. Jenkins 실패 시 local graph runner state artifact 생성 연결
25. Debug Agent tool/graph runner 보호용 pytest 추가
26. Debug Agent 로직을 agent_tools 패키지로 분리하고 scripts는 CLI wrapper로 정리
27. LangGraph StateGraph prototype 추가
28. Jenkins 실패 시 LangGraph state artifact 생성 연결
29. Jenkins failure post에서 .venv Python 사용하도록 수정
30. 의도적 실패/복구로 LangGraph state artifact 생성 확인
```

첫 실패도 기록했습니다.

```text
Failure:
Test stage에서 ModuleNotFoundError: No module named 'app'

Cause:
Jenkins pytest 실행 시 프로젝트 루트가 Python import path에 없었음.

Fix:
Jenkinsfile Test stage에서 PYTHONPATH=. pytest -q로 실행.
```

현재 성공한 수동 CI 흐름은 아래와 같습니다.

```text
Checkout
-> Install
-> Test
-> Build Image
-> Deploy skipped
-> SUCCESS
```

의도적으로 만든 실패/복구 흐름도 확인했습니다.

```text
app/main.py 응답을 broken으로 변경
-> Jenkins Test stage 실패
-> Console Output에서 실패 테스트 확인
-> debug-agent-input.md 생성 확인
-> app/main.py 응답 원복
-> Jenkins SUCCESS 재확인
```

현재 실패 빌드에서 보관하는 artifact는 아래와 같습니다.

```text
debug-agent-input.md
debug-agent-report.md
debug-graph-state.json
debug-langgraph-state.json
pytest-output.log
```

주의:

```text
Jenkins Install stage에서 설치한 Python dependency는 .venv 안에 있습니다.
failure post 단계에서 LangGraph를 실행하려면 python3 대신 .venv/bin/python을 우선 사용해야 합니다.
```

## Project Direction

파이널 프로젝트의 중심은 Python 기반 multi-agent platform입니다.

```text
Router Agent
-> Planner Agent
-> Data/RAG Agent
-> Work Agent
-> Reviewer Agent
-> eval report
```

이 저장소는 그 본 프로젝트의 부가 실험입니다.

```text
Jenkins console log
+ recent git diff
+ failed stage / failed test
-> Debug Agent
-> failure summary / suspected files / fix direction / patch draft
```

Jenkins를 쓰는 이유는 Java 개발을 하기 위해서가 아닙니다. Jenkins라는 CI/CD 서버가 Java로 실행되기 때문에 Jenkins 서버에 Java가 필요할 뿐이고, 실제 앱과 에이전트 실험은 Python 중심으로 진행합니다.

## Target Flow

```text
developer environment
-> GitHub
-> jenkins-server
-> vm1 deploy server
```

주의:

```text
PDF에 나온 VM1=Jenkins 방식으로 가지 말고,
Jenkins 서버와 배포 서버(vm1)를 분리하는 방식으로 진행한다.
```

역할은 아래처럼 고정합니다.

```text
developer environment
= 현재 WSL/Ubuntu 터미널
= 코딩, 로컬 테스트, git commit, git push

GitHub
= 코드 저장소

jenkins-server
= Jenkins 설치 서버
= repo checkout, pytest, Docker build, 실패 로그 생성

vm1 deploy server
= 나중에 앱 컨테이너가 실행될 서버
= Jenkins와 다른 별도 서버
```

## Current Scope

현재 1차 목표는 배포가 아니라 CI 성공과 실패 로그 확보입니다.

```text
완료:
Jenkins가 GitHub repo checkout
Jenkins에서 pytest 실행
Jenkins에서 Docker image build
수동 Build with Parameters 성공
의도적 실패 로그 확보
debug-agent-input.md 확인
docs/debug-agent-example.md 작성
scripts/debug_agent.py 초기 목업 작성
docs/debug-agent-report.md 생성 확인
Jenkins failure post 단계에서 debug-agent-report.md artifact 생성 연결
pytest-output.log를 Debug Agent 입력에 포함하도록 Jenkinsfile 개선
scripts/debug_agent.py 하드코딩 리포트 제거 및 실패 테스트/에러/변경 파일 추출형으로 개선
prompts/debug-agent-system.md와 prompts/debug-agent-user.md 추가
docs/tool-contract-debug-agent.md에 tool contract 정리
docs/langgraph-debug-agent-plan.md에 graph state/node/tool 경계 설계
scripts/run_debug_graph.py로 LangGraph 의존성 없는 local graph flow 작성
docs/virtualbox-network-notes.md에 Jenkins VM 네트워크와 Kubernetes 실습 병행 메모 정리
Jenkins failure post 단계에서 debug-graph-state.json artifact 생성 연결
tests/test_debug_agent.py와 tests/test_run_debug_graph.py 추가
agent_tools/debug_agent.py와 agent_tools/debug_graph.py에 실제 tool/graph 로직 분리
agent_tools/langgraph_debug.py와 scripts/run_langgraph_debug.py 추가
Jenkins failure post 단계에서 debug-langgraph-state.json artifact 생성 연결
Jenkins failure post 단계에서 .venv/bin/python 우선 사용하도록 수정
의도적 실패 후 debug-langgraph-state.json artifact 생성 확인
복구 후 Jenkins SUCCESS 재확인

다음:
debug-graph-state.json과 debug-langgraph-state.json 비교 자동화
나중에 OpenAI API 기반 Debug Agent로 확장
```

아직 하지 않을 것:

```text
GitHub webhook
vm1 자동 배포
운영 DB 연결
agent에게 배포 권한 부여
자동 merge/deploy
```

## Local Run

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

## Test

```bash
pip install -r requirements-dev.txt
PYTHONPATH=. pytest -q
```

## Docker Run

```bash
docker build -t cicd-practice-app:latest .
docker run --rm -p 8000:8000 cicd-practice-app:latest
```

## Jenkins Job

Jenkins job은 `Pipeline script from SCM` 방식으로 만듭니다.

```text
Repository URL:
https://github.com/hwc2000/cicd-practice-app.git

Branch:
*/main

Script Path:
Jenkinsfile
```

첫 수동 빌드에서는 Jenkins parameter `RUN_DEPLOY`를 체크하지 않습니다. 그러면 Jenkins는 checkout, install, test, Docker build까지만 실행하고 배포는 건너뜁니다.

배포 서버(vm1)를 준비한 뒤에만 `RUN_DEPLOY=true`로 실행합니다.

## Intentional Failure Practice

테스트 실패 로그를 만들고 싶으면 `app/main.py`의 응답을 잠깐 바꿉니다.

```python
return {"message": "broken"}
```

그 다음 commit/push 후 Jenkins에서 실패한 `Test` stage의 console log를 확인합니다.

Debug Agent 입력 후보:

```text
Jenkins console log
debug-agent-input.md
git diff
failed stage
failed test name
changed files
```

Debug Agent 출력 후보:

```text
failure summary
suspected files
fix direction
patch draft
human review checklist
```

## Debug Agent Prototype

현재 Debug Agent는 아직 LLM API를 호출하지 않는 로컬 목업입니다.

```text
Input:
docs/debug-agent-example.md

Script:
scripts/debug_agent.py

Output:
docs/debug-agent-report.md
```

실행 예시:

```bash
python3 scripts/debug_agent.py \
  --input docs/debug-agent-example.md \
  --output docs/debug-agent-report.md
```

현재 목업은 실패 테스트명, 에러 메시지, 의심 파일, 원인, 수정 방향, 패치 초안, 검증 명령을 리포트 형태로 정리합니다.

## Next Steps

```text
1. Jenkinsfile post failure에서 scripts/debug_agent.py 실행 연결
2. 실패 시 debug-agent-report.md를 artifact로 archive
3. Jenkins Console Output 일부를 Debug Agent 입력에 포함하도록 개선
4. OpenAI API 기반 Debug Agent로 확장
5. GitHub webhook 연결
6. 배포 서버(vm1)를 따로 만들고 RUN_DEPLOY=true 배포 실험
```
