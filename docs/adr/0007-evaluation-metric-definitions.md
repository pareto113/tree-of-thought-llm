# ADR-0007: 평가 메트릭 정의 — nodes_visited(Figure 3a) 및 answer_fmt_error(Figure 3b)

## 상태

채택

## 배경

`evaluate_log.py`에서 Figure 3(a)와 Figure 3(b)에 필요한 두 가지 메트릭을 계산해야 한다.
b=1 실험 분석 중 기존 구현에 두 가지 모호점이 발견되었다.

---

## 결정 1 — nodes_visited 정의 (Figure 3(a) x축)

**정의**: 한 퍼즐당 BFS 전체 steps에서 생성된 candidate 부분해의 수를 합산한 후, 퍼즐 수로 나눈 **퍼즐당 평균**.

```
nodes_visited = (sum over all puzzles, sum over all steps: len(step['new_ys'])) / n_puzzles
```

**근거**: 논문 원문 — *"nodes visited = number of partial solutions evaluated by GPT-4"*
- `new_ys`는 해당 step에서 value 함수가 평가한 모든 부분해 목록이므로 정의와 정확히 부합한다.
- API 요청 수(~43/퍼즐)나 LLM generation 수(n_evaluate_sample 포함 ~122/퍼즐)와는 다른 단위임에 주의.
- 퍼즐당 평균으로 스케일링하면 Figure 3(a)에서 IO/CoT의 k(샘플 수)와 같은 단위로 비교 가능하다.

**기각된 대안**:
- API 요청 수: 비용/레이턴시 분석에는 적합하나 논문 정의와 다름
- 전체 합산: 퍼즐 수가 다른 실험 간 비교 불가

---

## 결정 2 — answer_fmt_error 카테고리 (Figure 3(b))

**정의**: BFS 탐색이 `left: 24`에 도달했으나 최종 Answer 표현식이 수학적으로 틀린 경우.

**근거**: b=1 실험에서 13%가 이 케이스에 해당했다. 이는 탐색 알고리즘의 실패가 아니라 answer step에서의 표현식 작성 오류다. 기존 구현은 이를 `fail = len(entry['steps'])` (마지막 step 번호)로 처리했는데, b값마다 step 수가 다르므로 step 번호가 혼동을 준다.

Figure 3(b)의 목적이 "어느 탐색 단계에서 경로가 소멸되는가"이므로, 탐색 외 원인의 실패를 같은 분포에 섞으면 분석이 흐려진다.

**answer_fmt_error 판별 조건**:
1. `_tot_failure_step(entry)` 가 `None` 반환 (= BFS가 left=24에 도달한 경로 존재)
2. `infos[-1]['r'] == 0` (= 최종 답 검증 실패)

→ 위 두 조건이 모두 참이면 `answer_fmt_error`, 아니면 탐색 실패 step 번호.

**기각된 대안**:
- `correct`로 분류: 최종 오답이므로 부적절
- 현행 유지(마지막 step 번호): b값 간 비교 시 step 번호가 달라져 혼동

## 영향

- `evaluate_log.py`의 `analyze_step_failures()`에 `answer_fmt_error` 분기 추가
- 동일 함수에 `nodes_visited` 계산 추가
- eval JSON 출력에 두 값 모두 포함
