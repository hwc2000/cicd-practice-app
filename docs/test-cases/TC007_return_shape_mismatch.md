# Test Case 007: Return Shape Mismatch

## 날짜
2026-04-22

## 난이도
⭐⭐⭐ - 함수는 실행되지만 응답 계약이 깨지는 케이스

## 목표

서비스 로직은 돌아가는데 반환 dict의 key가 API 계약과 어긋나서 실패하는 상황을 검증합니다.

## 추천 재현 방식

정상 상태:

```text
id, name, price, quantity, discount_percent, total_price
```

의도적 버그:

```text
total_price -> total
```

또는 `total_price` 자체를 제거

## 예상 실패

```text
fastapi.exceptions.ResponseValidationError
Field required: total_price
```

또는 응답 shape 검증 테스트 실패

## 기대하는 에이전트 능력

1. traceback과 response_model 계약을 함께 읽기
2. 테스트 기대값이 아니라 실제 응답 key mismatch를 파악하기
3. 서비스 반환 dict를 원래 API 계약에 맞게 복구하기

## 목적

실무에서 흔한

```text
serializer drift
response contract regression
refactor 후 key rename 누락
```

을 검증하기 위한 TC입니다.
