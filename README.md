# cicd-practice-app

Jenkins CI/CD 흐름을 익히기 위한 최소 FastAPI 예제입니다.

## 흐름

```text
developer vm
-> GitHub
-> Jenkins
-> deploy server
```

## 로컬 실행

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

## 테스트

```bash
pytest
```

## Docker 실행

```bash
docker build -t cicd-practice-app:latest .
docker run --rm -p 8000:8000 cicd-practice-app:latest
```

## Jenkins에서 필요한 것

- GitHub repository URL
- GitHub webhook 설정
- Jenkins GitHub credential
- Jenkins에서 deploy server로 접속할 SSH credential
- deploy server에 Docker 설치

