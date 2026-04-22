# Test Case 009: Three-Bug Chain

## 날짜
2026-04-22

## 난이도
⭐⭐⭐⭐⭐ - 한 번의 실수 묶음으로 여러 단계 오류가 드러나는 케이스

## 목표

하나의 리팩터링에서 아래 세 문제가 같이 들어간 상황을 실험합니다.

## 버그 구성

1. `build_item_record()`가 새 필수 파라미터 `source`를 요구함
2. 반환 dict에서 `source` 필드 누락
3. `total_price`를 `total`로 잘못 rename

## 예상 흐름

```text
1차: TypeError
2차: ResponseValidationError(source 또는 total_price)
3차: 전체 통과
```

## 목적

retry loop 없이 한 번에 고칠 수 있는지,
아니면 재시도에서 컨텍스트를 갱신하며 수습하는지 확인하기 위한 TC입니다.
