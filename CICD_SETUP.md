# CI/CD 실습 순서

이 저장소는 파이널 프로젝트의 메인 기능이 아니라, Debug Agent / CI-CD Agent 확장을 위한 운영 로그 실험용 저장소입니다. 목표는 Jenkins 전문가가 되는 것이 아니라 Jenkins 실패 로그와 git diff를 에이전트 입력으로 만들어보는 것입니다.

## 전체 흐름

```text
개발자 환경
-> GitHub
-> jenkins-server
-> vm1 배포 서버
```

주의:

```text
PDF에 나온 VM1=Jenkins 방식으로 가지 말고,
Jenkins 서버와 배포 서버(vm1)를 분리하는 방식으로 진행한다.
```

역할:

- 개발자 환경: 현재 WSL/Ubuntu 터미널
- GitHub: 코드 저장소
- jenkins-server: Jenkins, git, python3, Docker로 CI 실행
- vm1 배포 서버: 나중에 앱 컨테이너 실행

## 1. 먼저 준비할 것

- GitHub 계정
- GitHub repository
- Jenkins 서버(jenkins-server)
- 배포 서버(vm1)
- Jenkins 서버에 Docker 설치
- 배포 서버 VM에 Docker 설치

처음 실습에서는 배포하지 않습니다. 먼저 Jenkins가 GitHub repo를 checkout하고 pytest와 Docker build를 수동으로 성공시키는 것만 확인합니다.

배포 단계는 `RUN_DEPLOY` Jenkins parameter를 켰을 때만 실행됩니다.

## 2. GitHub repository 만들기

개발자 VM에서 이 폴더를 별도 git repository로 만들고 GitHub에 push합니다.

```bash
cd /home/kyung/workspace/hw/academy/cicd-practice-app
git init
git add .
git commit -m "Add CI/CD practice app"
git branch -M main
git remote add origin git@github.com:YOUR_ID/cicd-practice-app.git
git push -u origin main
```

HTTPS remote를 쓰면 GitHub token이 필요할 수 있고, SSH remote를 쓰면 GitHub SSH key가 필요합니다.

## 3. GitHub token은 언제 필요한가

GitHub token은 보통 Jenkins가 GitHub와 통신할 때 씁니다.

필요한 경우:

- private repository를 Jenkins가 checkout해야 할 때
- Jenkins가 GitHub webhook을 자동 등록하게 하고 싶을 때
- Jenkins가 commit status를 GitHub에 다시 표시하게 하고 싶을 때

처음 실습에서는 public repository라면 token 없이도 checkout이 될 수 있습니다. 하지만 private repository로 할 거면 Jenkins credential에 GitHub token을 등록하는 게 좋습니다.

권한은 처음에는 최소로 잡습니다.

- repository 읽기 권한
- webhook 관리가 필요하면 webhook 관련 권한

## 4. Jenkins credential 두 종류

Jenkins에는 credential이 최소 2개 필요할 수 있습니다.

### GitHub 접근용 credential

용도:

- Jenkins가 GitHub repository를 checkout

종류:

- GitHub username + token
- 또는 SSH private key

### 배포 서버 SSH credential

용도:

- Jenkins가 배포 서버 VM에 `scp`, `ssh` 실행

종류:

- SSH private key

이 예제의 Jenkinsfile은 배포 서버 credential ID를 아래 이름으로 기대합니다.

```text
deploy-server-ssh-key
```

Jenkins credential에 등록할 때 ID를 똑같이 맞추면 됩니다.

## 5. Jenkins job 만들기

추천 job 타입:

```text
Pipeline
```

처음에는 아래 순서로 잡는 게 쉽습니다.

1. Jenkins에서 새 item 생성
2. Pipeline 선택
3. Pipeline script from SCM 선택
4. SCM은 Git 선택
5. GitHub repository URL 입력
6. credential 선택
7. Branch는 `*/main`
8. Script Path는 `Jenkinsfile`
9. 저장
10. Build Now로 수동 실행

수동 실행이 먼저 성공해야 webhook을 붙이는 게 편합니다.

처음 Build Now에서는 `RUN_DEPLOY`를 체크하지 않습니다. 그러면 배포 서버(vm1)가 없어도 checkout, install, test, Docker build까지만 확인할 수 있습니다.

## 6. 배포 서버를 붙일 때 Jenkinsfile에서 바꿀 값

`Jenkinsfile`의 이 값을 실제 배포 서버에 맞게 바꿉니다.

```groovy
DEPLOY_HOST = 'CHANGE_ME_DEPLOY_SERVER_IP'
DEPLOY_USER = 'CHANGE_ME_USER'
```

예시:

```groovy
DEPLOY_HOST = '192.168.56.20'
DEPLOY_USER = 'ubuntu'
```

배포 서버(vm1)를 준비하기 전에는 이 값을 바꾸지 않아도 됩니다.

## 7. GitHub webhook 설정

Jenkins job이 수동으로 성공한 뒤 webhook을 붙입니다.

GitHub repository에서:

```text
Settings
-> Webhooks
-> Add webhook
```

Payload URL:

```text
http://JENKINS_HOST:8080/github-webhook/
```

Content type:

```text
application/json
```

Event:

```text
Just the push event
```

Jenkins 서버가 GitHub에서 접근 가능한 주소여야 합니다. 로컬 VM이라 외부에서 접근이 안 되면 webhook이 실패할 수 있습니다. 그 경우에는 ngrok 같은 터널을 쓰거나, 일단 Jenkins에서 수동 빌드로 실습해도 됩니다.

## 8. 일부러 실패시키는 연습

`app/main.py`에서 응답을 바꿔서 테스트를 깨뜨립니다.

```python
return {"message": "broken"}
```

그 다음 push합니다.

```bash
git add .
git commit -m "Break root response"
git push
```

Jenkins에서 `Test` stage가 실패하는지 확인합니다.

이 실패 로그와 Jenkins artifact의 `debug-agent-input.md`가 나중에 Debug Agent의 입력이 됩니다.

## 9. CI/CD 에이전트로 확장할 때 입력

처음 에이전트는 배포 권한을 갖지 않고 로그 분석만 하게 둡니다.

입력 후보:

- Jenkins console log
- 최근 git diff
- 실패한 stage 이름
- 실패한 테스트 이름
- 변경 파일 목록

출력 후보:

- 실패 원인 요약
- 의심 파일
- 수정 방향
- patch 초안
- 사람이 확인해야 할 점
