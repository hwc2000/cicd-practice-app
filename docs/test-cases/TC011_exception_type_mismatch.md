# Test Case 011: Exception Type Mismatch

## 날짜
2026-04-22

## 난이도
⭐⭐⭐ - 상태 코드는 맞아야 하는데 일반 예외가 터지는 케이스

## 목표

없는 리소스를 조회할 때 API가 `404 HTTPException` 대신 일반 Python 예외를 던져
테스트와 실제 API 계약이 깨지는 상황을 검증합니다.

## 정상 기대 동작

```text
GET /items/999
-> 404
-> {"detail": "Item 999 not found"}
```

## 의도적 버그

```text
raise HTTPException(...)
-> raise ValueError(...)
```

## 예상 실패

```text
ValueError: Item 999 not found
```

또는 테스트 클라이언트에서 서버 예외 전파로 테스트 실패

## 기대하는 에이전트 능력

1. traceback에서 예외 타입이 잘못됐음을 파악하기
2. FastAPI endpoint에서 올바른 `HTTPException` 패턴으로 복구하기
3. 상태 코드와 detail 메시지를 함께 유지하기

## 목적

실무에서 자주 나오는

```text
예외 타입 회귀
상태 코드 누락
프레임워크 계약 위반
```

을 검증하기 위한 TC입니다.
