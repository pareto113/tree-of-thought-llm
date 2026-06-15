# 시각화 결정 — plot_figures.py

`plot_figures.py`는 논문 Figure 3(a)/(b)에 대응하는 그래프와 본 실험 고유의 추가 그래프를 생성한다.
이 ADR은 코드만 보면 이해하기 어려운 네 가지 결정을 기록한다.

---

## 결정 1: CoT Figure 3(b) 수치 — Ans. fmt error 3%, Correct 4%

초기 instruction에는 CoT의 `Ans. fmt = 0.00`, `Correct = 0.07`로 기재되어 있었다.
실제 로그 분석(`scripts/diagnose_cot_correct.py`)을 통해 다음과 같이 수정했다.

| 항목 | 초기 instruction | 실제 수치 |
|------|-----------------|---------|
| Ans. fmt error | 0.00 | **0.03** |
| Correct | 0.07 | **0.04** |

**원인**: CoT "성공" 판정에 두 가지 기준이 혼재했다.

- **step 분석 기준** (`_cot_failure_step`): CoT 중간 경로에서 `left: 24`에 도달하면 성공으로 판정.
  7개 퍼즐이 이 기준을 통과했다.
- **Table 2 기준** (`accs`): 최종 `Answer: (수식) = 24` 표현식을 독립적으로 수학 검증.
  4개 퍼즐만 이 기준을 통과했다.

차이 3건 = 중간 경로는 24에 도달했으나 최종 Answer 표현식이 수학적으로 틀린 경우.
이것이 CoT의 `answer_fmt_error`다.

Figure 3(b)의 CoT 데이터는 Table 2와 일관된 **Table 2 기준(Correct = 4%)** 을 사용한다.

---

## 결정 2: Figure 3(a) best-of-k 곡선 — k=1~100 전수 계산

논문 원본 Figure 3(a)의 IO/CoT best-of-k 곡선은 여러 k값에서의 성공률을 선으로 연결한다.
초기 instruction은 "중간 k값 집계가 어려우면 두 점 (k=1, k=100)만 직선으로 연결"을 대안으로 제시했다.

IO×100, CoT×100 로그의 각 퍼즐 entry에 k=100개의 샘플 결과(`infos[i]['r']`)가 모두 저장되어 있어,
k=1부터 100까지 best-of-k를 전수 계산할 수 있었다.

직선 연결 대신 전수 계산을 선택한 이유: 실제 곡선은 초반(k=1~20)에 급격히 상승하고
이후 완만해지는 로그 형태를 보이는데, 직선 연결은 이 특성을 숨긴다.
전수 계산으로 매끄러운 실제 곡선을 재현했다.

---

## 결정 3: 추가 그래프 — b값별 성공/오류 분포 (figure_b_breakdown.png)

논문 Figure 3에는 존재하지 않는 추가 그래프다. b=1~5 각각에 대해
성공(Correct) / Answer 형식 오류(Ans. fmt error) / Step 실패의 세 카테고리를 stacked bar로 시각화한다.

이 그래프를 추가한 이유: b가 커질수록 step 실패가 줄고 Ans. fmt error가 늘어나는 패턴이
GPT-4o mini ToT의 핵심 병목을 보여주는 본 실험 고유의 발견이기 때문이다.
텍스트 서술만으로는 이 추세가 직관적으로 전달되기 어려워 별도 그래프로 시각화했다.

| b | Correct | Ans. fmt error | Step 실패 |
|---|---------|---------------|---------|
| 1 | 26% | 13% | 61% |
| 2 | 27% | 9% | 64% |
| 3 | 44% | 15% | 41% |
| 4 | 52% | 19% | 29% |
| 5 | 60% | 24% | 16% |

---

## 결정 4: Figure 3(a)와 3(b)를 별도 파일로 저장

논문 원본은 3(a)와 3(b)를 하나의 Figure에 나란히 배치한다.
Word 삽입 시 개별 그래프 크기 조절 편의를 위해 `figure3a.png`, `figure3b.png`로 분리 저장한다.
나란히 배치가 필요할 경우 Word에서 직접 조합하면 된다.
