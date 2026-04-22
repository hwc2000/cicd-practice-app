# Test Case 002: Missing Import (서비스가 유틸 함수를 쓰는데 import 누락)

## 날짜
2026-04-22

## 난이도
⭐⭐ (중하) - 단일 파일 수정, import 1줄 복구

## 시나리오

`app/services.py`는 상품 이름 정규화를 위해 `app/utils.py`의 `normalize_item_name()`을 사용합니다.

정상 코드:

```python
from app.utils import normalize_item_name
```

이 import 줄을 실수로 지우면 `create_item()` 호출 시 런타임에서 `NameError`가 발생합니다.

## 재현 방법

의도적으로 아래 한 줄을 제거합니다.

```python
from app.utils import normalize_item_name
```

그 뒤 `pytest -q` 또는 Jenkins 빌드를 실행합니다.

## 예상 실패 형태

```text
FAILED tests/test_main.py::test_create_item - NameError: name 'normalize_item_name' is not defined
FAILED tests/test_main.py::test_create_item_normalizes_name - NameError: name 'normalize_item_name' is not defined
```

## 에이전트가 해야 하는 일

1. 실패는 `tests/test_main.py`에서 보이지만 수정은 `app/services.py`에서 해야 함
2. `normalize_item_name` 심볼이 정의되지 않았다는 점을 보고 missing import로 해석해야 함
3. 새 로직을 만들지 말고 기존 `app/utils.py`의 함수를 import해서 연결해야 함

## 기대 결과

- Auto-fix가 `app/services.py`에 `from app.utils import normalize_item_name`를 복구
- pytest 전체 통과
- git push 후 검증 빌드 SUCCESS
