# Test Case 004: Pydantic 응답 필드 불일치

## 날짜
2026-04-22

## 난이도
⭐⭐⭐ - 응답 모델 계약과 실제 반환 데이터 불일치

## 현재 정상 상태

`ItemResponse`는 아래 필드를 포함합니다.

```text
id
name
price
quantity
discount_percent
total_price
source
```

현재 서비스 레이어도 `source: "api"`를 포함해서 정상 응답을 반환합니다.

## 나중에 만들 실패 예시

예를 들어 `app/models.py`의 `ItemResponse`에는 `source`가 남아 있는데,
`app/services.py`에서 반환하는 item dict에서 `source`를 빠뜨리면 FastAPI/Pydantic 응답 검증이 깨집니다.

예상 증상:

```text
fastapi.exceptions.ResponseValidationError
Field required: source
```

## 기대하는 에이전트 동작

1. 실패가 endpoint 테스트에서 보이더라도 실제 수정 지점은 모델 또는 서비스 계약임을 파악
2. 테스트를 바꾸지 않고 `ItemResponse`와 실제 반환 dict를 다시 일치시킴
3. 응답 계약을 유지한 채 pytest를 통과시킴

## 목적

이 케이스는 단순 문자열 치환이 아니라,

```text
Pydantic schema
vs
runtime response payload
```

사이 계약 불일치를 LLM이 복구할 수 있는지 보기 위한 TC입니다.
