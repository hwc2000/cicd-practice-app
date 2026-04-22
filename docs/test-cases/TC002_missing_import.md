# Test Case 002: Missing Import 성공 기록

## 날짜
2026-04-22

## 난이도
⭐⭐ (중하) - 단일 파일 수정, import 1줄 복구

## 시나리오

실험 당시 `app/services.py`는 `app/utils.py`의 `normalize_item_name()`을 사용하도록 구성했고, 의도적으로 import 한 줄을 제거해서 실패를 만들었습니다.

버그 형태:

```python
from app.utils import normalize_item_name
```

이 줄을 제거하면 `create_item()` 호출 시 `NameError`가 발생했습니다.

## 실패 형태

```text
FAILED tests/test_main.py::test_create_item - NameError: name 'normalize_item_name' is not defined
FAILED tests/test_main.py::test_create_item_normalizes_name - NameError: name 'normalize_item_name' is not defined
```

## 실제 결과

```text
61번 빌드 FAILURE
-> Jenkins artifact 생성
-> OpenAI auto-fix가 missing import를 복구
-> auto commit / push
-> 62번 빌드 자동 생성
-> 62번 SUCCESS
```

## 의미

- TC002는 하드코딩된 전용 규칙을 추가해서 맞춘 케이스가 아니라, 현재 OpenAI auto-fix 경로가 import 누락을 읽고 복구한 케이스로 확인함
- 이후 TC003, TC004, TC005도 같은 방식으로 실제 실패를 만들고 auto-fix loop를 검증할 예정

## 정리

- TC002 실험용 코드와 테스트는 실험 종료 후 제거
- 문서만 성공 기록으로 유지
