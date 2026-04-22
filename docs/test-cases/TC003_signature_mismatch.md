# Test Case 003: 함수 시그니처 변경 불일치

## 날짜
2026-04-22

## 난이도
⭐⭐⭐⭐ - 함수 정의/호출부 사이 계약 불일치, `TypeError` 복구

## 시나리오

`app/services.py`에서 `create_item()`은 내부적으로 `build_item_record()`를 호출합니다.

현재 정상 흐름:

```text
create_item(...)
-> calculate_total_price(...)
-> build_item_record(...)
-> item dict 반환
```

이 구조에서 `build_item_record()`의 시그니처를 바꾸고 `create_item()` 호출부를 같이 업데이트하지 않으면 `TypeError`가 발생합니다.

## 나중에 만들 실패 예시

예를 들어 `build_item_record()`를 아래처럼 바꿨다고 가정합니다.

```python
def build_item_record(
    item_id: int,
    name: str,
    price: float,
    quantity: int,
    discount_percent: float,
    total_price: float,
    source: str,
) -> dict[str, Any]:
```

그런데 `create_item()`에서 `source=`를 넘기지 않으면:

```text
TypeError: build_item_record() missing 1 required positional argument: 'source'
```

## 기대하는 에이전트 동작

1. traceback에서 깨진 함수 호출 지점을 찾는다
2. 함수 정의와 호출부를 비교한다
3. 테스트를 억지로 바꾸지 말고 호출부 또는 정의부를 일관되게 맞춘다
4. pytest 재검증 후 자동 복구를 끝낸다

## 목적

이 케이스는 단순 값 치환이 아니라:

```text
함수 정의
vs
호출부
```

사이 계약 불일치를 LLM이 읽고 고칠 수 있는지 확인하기 위한 TC입니다.
