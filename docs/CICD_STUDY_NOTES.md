# CI/CD 자동 복구 에이전트 — 학습 정리 & 면접 포인트

> 이 문서는 CI/CD 파이프라인 실습 + AI 자동 복구 에이전트 구현 과정을 정리한 노션용 문서입니다.

---

## 1. CI/CD란?

### 핵심 개념

| 용어 | 의미 | 예시 |
|------|------|------|
| **CI (Continuous Integration)** | 코드 변경 시 자동으로 빌드 + 테스트 | push → Jenkins가 pytest 실행 |
| **CD (Continuous Delivery)** | CI 통과 후 자동으로 배포 준비 | Docker 이미지 빌드 + 서버 전송 |
| **CD (Continuous Deployment)** | 배포까지 완전 자동화 | 이미지를 프로덕션 서버에 자동 배포 |

### 💡 면접 포인트
> **Q: CI/CD를 왜 사용하나요?**
>
> A: 수동 빌드/배포 과정에서 발생하는 휴먼 에러를 줄이고, 코드 변경 시마다 자동으로 테스트를 돌려서 빠르게 문제를 발견합니다. "코드를 push하면 10분 안에 문제가 있는지 알 수 있다"는 것이 CI의 핵심 가치입니다.

---

## 2. 파이프라인 구조

### 우리가 구현한 파이프라인

```text
Developer (로컬)
  → git push
  → GitHub (코드 저장소)
  → Jenkins (CI 서버, VirtualBox VM)
     Stage 1: Checkout    — GitHub에서 코드 가져옴
     Stage 2: Install     — Python 가상환경 + 의존성 설치
     Stage 3: Test        — pytest 실행
     Stage 4: Build Image — Docker 이미지 빌드
     Stage 5: Deploy      — (선택) 배포 서버로 전송
```

### 💡 면접 포인트
> **Q: Jenkins 파이프라인을 직접 구성해본 경험이 있나요?**
>
> A: 네. Jenkinsfile을 작성해서 SCM(GitHub)에서 코드를 가져오고, Python 가상환경에서 pytest 테스트 실행, Docker 이미지 빌드까지 자동화했습니다. `Pipeline script from SCM` 방식으로 Jenkinsfile 자체도 버전 관리했습니다.

---

## 3. Jenkinsfile — 핵심 이해

### Jenkinsfile이란?
파이프라인을 코드로 정의하는 파일. **"Pipeline as Code"**.

```groovy
pipeline {
    agent any                    // 어떤 Jenkins 노드에서 실행
    parameters { ... }           // 빌드 파라미터 (체크박스 등)
    stages {
        stage('Test') { ... }    // 각 단계 정의
    }
    post {
        failure { ... }          // 실패 시 실행할 로직
    }
}
```

### 우리가 사용한 핵심 기능

| 기능 | 설명 | 우리 사용 예 |
|------|------|-------------|
| `parameters` | 빌드 시 사용자 입력 | `AUTOFIX_ENABLED` 체크박스 |
| `post { failure {} }` | 실패 시 후처리 | 에러 수집 → auto-fix 실행 |
| `withCredentials` | 보안 정보 주입 | GitHub token, OpenAI key |
| `build job` | 다른 빌드 트리거 | 검증 빌드 자동 시작 |
| `archiveArtifacts` | 결과물 보관 | 분석 리포트, 패치 결과 |

### 💡 면접 포인트
> **Q: Jenkinsfile의 장점은?**
>
> A: 파이프라인 설정이 코드로 관리되므로 버전 관리가 가능하고, PR 리뷰 대상이 됩니다. Jenkins UI에서 수동으로 설정하면 변경 이력이 남지 않지만, Jenkinsfile은 git log로 "누가, 언제, 왜 파이프라인을 바꿨는지" 추적할 수 있습니다.

---

## 4. 자동 복구 에이전트 — 핵심 설계

### 왜 만들었나?

기존 CI 실패 대응 흐름:
```text
빌드 실패 → 개발자가 로그 확인 → 원인 분석 → 코드 수정 → push → 재빌드 → (또 실패) → 반복
```

자동 복구 에이전트 적용 후:
```text
빌드 실패 → 에이전트가 로그 수집 + 소스코드 분석 → 자동 수정 → pytest 검증 → push → 재빌드 → 성공
```

### Auto-Fix 루프 설계

```text
collect_error     에러 로그 + git diff 수집
     ↓
analyze_failure   실패 테스트, 에러 라인, 의심 파일 추출 (rule-based)
     ↓
generate_fix      수정안 생성 (OpenAI + rule-based fallback)
     ↓
apply_fix         파일에 패치 적용 (원본 백업)
     ↓
run_tests         pytest 로컬 재검증
     ↓
decide_next       → 통과: commit_push
                  → 실패 & retry 남음: retry (원본 복원 후 재시도)
                  → retry 소진: give_up
```

### 💡 면접 포인트
> **Q: 이 프로젝트에서 가장 어려웠던 부분은?**
>
> A: 두 가지가 있었습니다.
> 1. **Jenkins의 detached HEAD 문제**: Jenkins는 SCM checkout 시 브랜치가 아닌 특정 커밋을 checkout합니다(detached HEAD). auto-fix로 수정한 코드를 push할 때 `git checkout main`이 실패하는 문제가 있어서, `git push HEAD:refs/heads/main`으로 해결했습니다.
> 2. **OpenAI 패치 정확도**: LLM이 생성한 `find` 문자열이 소스코드의 들여쓰기(공백)까지 정확히 일치해야 패치가 적용됩니다. 프롬프트에 "소스코드에서 정확히 존재하는 부분을 복사할 것"을 명시해서 해결했습니다.

---

## 5. 수정안 생성 전략 — Rule-based + LLM 하이브리드

### 왜 둘 다 쓰나?

| 방식 | 장점 | 단점 |
|------|------|------|
| **Rule-based** | 빠르고 정확, API 비용 없음 | 정해진 패턴만 대응 |
| **OpenAI (LLM)** | 다양한 에러 패턴 대응 | 느리고, 비용 발생, 오답 가능 |

**전략: OpenAI 우선, rule-based fallback**

```python
def generate_fix(state):
    # 1) OpenAI (소스코드 읽혀서 범용 수정안 생성)
    patch = try_openai_fix(state)
    if patch:
        return patch
    # 2) Rule-based fallback (하드코딩된 패턴만)
    return analysis.get("patch_candidate")
```

### 💡 면접 포인트
> **Q: LLM으로 코드를 수정하는 것이 안전한가요?**
>
> A: 자체적으로 안전장치를 두었습니다.
> - 수정 전 원본 파일을 백업하고, 실패 시 자동 롤백합니다.
> - 수정 후 반드시 pytest를 돌려서 통과해야만 push합니다.
> - 테스트 코드를 수정해서 통과시키는 것은 프롬프트에서 금지했습니다.
> - 검증 빌드는 `AUTOFIX_ENABLED=false`로 실행해서 무한 루프를 방지합니다.
> - retry 최대 3회로 제한합니다.

---

## 6. 인프라 구성

```text
┌─────────────────────────┐
│  Developer (WSL/Ubuntu)  │
│  코딩 + git push         │
└──────────┬──────────────┘
           │ git push
           ▼
┌─────────────────────────┐
│  GitHub                  │
│  코드 저장소             │
└──────────┬──────────────┘
           │ SCM checkout
           ▼
┌─────────────────────────┐
│  Jenkins Server          │
│  (VirtualBox VM)         │
│  192.168.56.10:8080      │
│  Host-only network       │
│                          │
│  역할:                   │
│  - pytest 실행           │
│  - Docker build          │
│  - Auto-fix 에이전트     │
│  - 검증 빌드 트리거      │
└─────────────────────────┘
```

### 💡 면접 포인트
> **Q: GitHub Webhook을 왜 안 쓰셨나요?**
>
> A: Jenkins 서버가 VirtualBox의 Host-only 네트워크(192.168.56.10)에 있어서 GitHub에서 접근이 불가능합니다. Webhook은 GitHub이 Jenkins로 HTTP 요청을 보내는 방식인데, 로컬 VM은 인터넷에서 도달할 수 없습니다. 대신 Jenkins의 `build job` Groovy 함수로 같은 서버 내에서 재빌드를 트리거했습니다. ngrok 같은 터널링을 쓰면 해결 가능하지만) 학습 목적이라 생략했습니다.

---

## 7. Git 운영 — 배운 것들

### Jenkins의 Detached HEAD

```text
일반 checkout:   git checkout main → main 브랜치 위에 HEAD
Jenkins checkout: git checkout -f <commit-hash> → detached HEAD (브랜치 없음)
```

Auto-fix에서 push할 때:
```bash
# ❌ 실패 (detached HEAD에서 main 브랜치로 전환 → 로컬 변경 충돌)
git checkout main
git push origin main

# ✅ 성공 (현재 HEAD의 커밋을 remote main에 직접 push)
git push origin HEAD:refs/heads/main
```

### .gitignore의 중요성

Jenkins workspace에서 `git add -A`를 하면 **빌드 아티팩트**(Docker 이미지 .tar, 테스트 로그, JSON 결과)까지 커밋됩니다. `.gitignore`로 제외하고 `git add`도 코드 디렉토리만 대상으로 변경했습니다.

### 💡 면접 포인트
> **Q: CI에서 자동 commit/push를 할 때 주의할 점은?**
>
> A: 세 가지가 있습니다.
> 1. **인증**: HTTPS push에는 GitHub token이 필요하고, Jenkins credential로 안전하게 관리합니다. 코드에 토큰을 노출하면 안 됩니다.
> 2. **무한 루프 방지**: 자동 push가 다시 빌드를 트리거하면 무한 반복될 수 있습니다. 검증 빌드에서는 `AUTOFIX_ENABLED=false`로 설정합니다.
> 3. **아티팩트 혼입 방지**: `git add -A` 대신 코드 폴더만 add하고, `.gitignore`로 빌드 결과물을 제외합니다.

---

## 8. 테스트 전략

### 테스트 계층

```text
단위 테스트 (services.py)
  → calculate_total_price 함수 직접 검증
  → 할인 0%, 10%, 50%, 100% 케이스

통합 테스트 (main.py endpoints)
  → FastAPI TestClient로 HTTP 요청/응답 검증
  → CRUD + 에러 핸들링 + 입력 검증(422)

Auto-fix 테스트 (autofix_graph.py)
  → 각 노드 단위 테스트 (collect, analyze, fix, test, decide)
  → 전체 루프 E2E 테스트 (broken → fixed → commit_push)
  → 패치 없을 때 give_up 확인
```

### 💡 면접 포인트
> **Q: 테스트를 어떻게 구성하셨나요?**
>
> A: 3개 계층으로 나눴습니다. 비즈니스 로직 단위 테스트(할인 계산), API 통합 테스트(FastAPI TestClient), Auto-fix 파이프라인 E2E 테스트. 총 33개 테스트로 전체 코드를 커버합니다. 특히 Auto-fix 테스트는 tmp 디렉토리에 가상 워크스페이스를 만들어서 실제 패치 적용 → pytest 실행까지 end-to-end로 검증합니다.

---

## 9. 검증된 Auto-Fix 케이스

| 케이스 | 에러 유형 | 수정 방식 | 결과 |
|--------|---------|----------|------|
| `"broken"` → `"hello cicd"` | 단순 return 값 변경 | Rule-based | ✅ 1회 성공 |
| `"unhealthy"` → `"ok"` | 다른 엔드포인트 값 변경 | OpenAI | ✅ 1회 성공 |
| 할인 계산 `+` → `-` | 다중 파일 수식 로직 버그 | OpenAI | ✅ 1회 성공 |

---

## 10. 기술 스택 정리

| 기술 | 용도 | 선택 이유 |
|------|------|----------|
| **Jenkins** | CI/CD 서버 | 업계 표준, 학습 목적 |
| **FastAPI** | 앱 프레임워크 | 비동기 + 자동 문서 + Pydantic |
| **pytest** | 테스트 | Python 표준 테스트 프레임워크 |
| **Docker** | 컨테이너화 | 환경 일관성, 배포 용이 |
| **OpenAI API** | LLM 기반 코드 분석 | 소스코드 이해 + 패치 생성 |
| **Pydantic** | 데이터 검증 | FastAPI 통합, 타입 안전 |
| **LangGraph** | 에이전트 그래프 | 상태 기반 워크플로 관리 |
| **VirtualBox** | 가상화 | 로컬에서 Jenkins 서버 운영 |

---

## 11. 프로젝트 의의 & 포트폴리오 어필 포인트

### 이 프로젝트가 보여주는 역량

1. **CI/CD 파이프라인 설계 및 구현** — Jenkinsfile 직접 작성, 파라미터화된 빌드
2. **DevOps 실무 문제 해결** — detached HEAD, credential 관리, 아티팩트 관리
3. **AI/LLM 실무 응용** — 단순 챗봇이 아닌, CI 파이프라인에 LLM을 통합한 자동화
4. **안전한 자동화 설계** — 무한 루프 방지, 원본 백업, pytest 검증 후 커밋
5. **테스트 주도 개발** — 33개 테스트로 전체 시스템 커버
6. **점진적 확장** — rule-based → OpenAI → retry loop 순으로 기능 확장

### 💡 면접에서 한 줄 요약
> "Jenkins CI 빌드가 실패하면 AI 에이전트가 자동으로 소스 코드를 분석하고, 수정하고, 테스트를 돌려서 통과하면 자동으로 push하는 시스템을 만들었습니다."
