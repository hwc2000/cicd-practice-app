# Test Case 005: 다중 버그 체인

## 날짜
2026-04-22

## 난이도
⭐⭐⭐⭐⭐ - 한 개를 고치면 다음 버그가 드러나는 chained failure

## 목표

한 번의 CI 실패에 버그가 하나만 있는 것이 아니라,
첫 번째 버그를 고친 뒤에야 두 번째 버그가 드러나는 상황을 실험합니다.

## 추천 조합

### 버그 1: 함수 시그니처 불일치

`build_item_record()`에 새 필수 파라미터를 추가하고 `create_item()` 호출부는 그대로 둡니다.

예상 1차 실패:

```text
TypeError: build_item_record() missing 1 required positional argument
```

### 버그 2: 응답 필드 불일치

그다음 `source` 필드를 반환 dict에서 제거해 둡니다.

버그 1이 해결되면 예상 2차 실패:

```text
fastapi.exceptions.ResponseValidationError
Field required: source
```

## 기대 시나리오

```text
1차 auto-fix
-> signature mismatch 수정
-> pytest 재실행
-> 숨겨진 field mismatch 노출
-> retry
-> 2차 auto-fix
-> 전체 통과
```

## 기대하는 에이전트 능력

1. 첫 번째 traceback 기준으로 우선순위 높은 에러부터 해결
2. 재실행 후 새 오류를 읽고 두 번째 수정안 생성
3. 한 번의 patch로 끝나지 않아도 retry loop로 수습

## 목적

이 케이스는 단일 버그 auto-fix가 아니라,

```text
sequential debugging
retry loop quality
context refresh
```

를 검증하기 위한 TC입니다.
