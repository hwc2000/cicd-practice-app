# Test Case 001: 할인 계산 로직 버그 (다중 파일, 수식 오류)

## 날짜
2026-04-22

## 난이도
⭐⭐⭐ (중상) — 다중 파일, 비즈니스 로직 버그, 수식 연산자 1글자 수정

## 실패 설명

`app/services.py`의 `calculate_total_price()` 함수에서 할인 금액을 **빼야 하는데 더하는 버그**.

```python
# 버그 코드 (services.py:27)
total = subtotal + discount_amount  # ← + 가 아니라 - 이어야 함
```

### 영향 범위
- 단위 테스트 3개 실패 (calculate_total_price 직접 검증)
- 엔드포인트 테스트 1개 실패 (POST /items → total_price 검증)
- 총 4개 실패, 10개 통과

### 에러 메시지 예시
```
FAILED test_calculate_total_with_discount - assert 220.0 == 180.0
FAILED test_calculate_total_full_discount - assert 400.0 == 0.0
FAILED test_calculate_total_half_discount - assert 300.0 == 100.0
FAILED test_create_item - assert 220.0 == 180.0
```

## OpenAI Auto-Fix에 요구되는 능력

1. **다중 파일 분석**: 에러는 `tests/test_main.py`에서 발생하지만, 수정은 `app/services.py`에 해야 함
2. **수식 이해**: `+ discount_amount` → `- discount_amount` (연산자 1글자 수정)
3. **테스트 코드 수정 금지**: 테스트 assertion 값은 올바르므로 소스 코드를 고쳐야 함

## 기대 결과

- Auto-fix가 `app/services.py`의 `+` → `-` 수정
- pytest 전체 통과
- git push → 검증 빌드 SUCCESS

## 실제 결과

> 빌드 #54 → auto-fix → #55 SUCCESS ✅

### Auto-fix 동작

| 단계 | 결과 | 비고 |
|------|------|------|
| Rule-based 분석 | ❌ 매칭 실패 | message 패턴만 지원 |
| OpenAI 패치 생성 | ✅ 성공 | `+` → `-` 정확히 수정 |
| 로컬 pytest 검증 | ✅ 전체 통과 | 14 passed |
| git push | ✅ 성공 | HEAD:refs/heads/main |
| 검증 빌드 #55 | ✅ SUCCESS | 자동 트리거 |

### OpenAI가 적용한 패치

```diff
-    # BUG: discount is added instead of subtracted
     subtotal = price * quantity
     discount_amount = subtotal * (discount_percent / 100)
-    total = subtotal + discount_amount  # should be subtotal - discount_amount
+    total = subtotal - discount_amount
     return round(total, 2)
```

### 시행착오

- 없음 — 1회 시도로 성공 (attempt 1/3)
- OpenAI가 버그 코멘트(`# BUG:`, `# should be`)도 함께 제거해서 코드를 깔끔하게 정리함
