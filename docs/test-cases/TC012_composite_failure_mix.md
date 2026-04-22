# Test Case 012: Composite Failure Mix

## 날짜
2026-04-22

## 난이도
⭐⭐⭐⭐⭐ - 여러 종류의 실수가 동시에 들어간 복합 케이스

## 포함한 실패 유형

1. 설정/기본값 오류
2. 예외 타입 또는 상태 코드 계약 오류
3. 함수 rename 또는 호출 mismatch
4. 응답 shape drift
5. 실무형 기본 상수 회귀

## 이번 주입 버전

- `discount_percent` 기본값이 `0`에서 `5`로 바뀜
- 없는 item 조회가 `404` 대신 `400`과 잘못된 detail을 반환
- `create_item()`이 없는 `resolve_item_source()`를 호출
- 응답 모델이 요구하는 `source`, `total_price` 계약을 서비스가 책임지도록 유지

## 목적

한 번의 auto-fix가 어디까지 맥락을 넓게 읽고 복구하는지 보기 위한 케이스입니다.
