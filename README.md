# cicd-practice-app

FastAPI 기반 CI/CD 실습 앱입니다. 이 저장소의 목적은 Jenkins 자체를 깊게 학습하는 것이 아니라, 나중에 만들 Debug Agent / CI-CD Agent가 읽을 수 있는 실제 CI 실패 로그와 git diff를 만들어보는 것입니다.

## Current Status

2026-04-16 기준으로 아래까지 완료했습니다.

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

다음:
일부러 테스트 실패 만들기
Jenkins console log와 git diff를 Debug Agent 입력으로 사용
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

## Next Steps

```text
1. 현재 성공 상태를 기준점으로 유지
2. app/main.py를 일부러 깨뜨려 Test stage 실패 만들기
3. Jenkins Console Output과 debug-agent-input.md 수집
4. 실패 로그 + git diff를 Debug Agent 입력 형식으로 정리
5. Debug Agent가 실패 원인, 의심 파일, 수정 방향을 설명하게 하기
6. 수동 실패/복구 흐름이 익숙해지면 GitHub webhook 연결
7. 마지막으로 배포 서버(vm1)를 따로 만들고 RUN_DEPLOY=true 배포 실험
```
