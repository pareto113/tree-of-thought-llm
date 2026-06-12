# GPT-4o mini 적용 실험 계획 — Game24

## 목적

Yao et al. (2023) Tree of Thoughts 논문의 Game24 실험을 GPT-4o mini에 적용한다.  
GPT-4 대비 GPT-4o mini에서 IO / CoT / ToT 방법론의 성능 차이를 비교한다.  
(재현 실험이 아닌 **적용 실험** — ADR-0001 참조)

---

## 실험 조건

| 항목 | 값 | 논문 원본 |
|------|-----|---------|
| 모델 | `gpt-4o-mini` | GPT-4 (Chat Completion mode) |
| 태스크 | Game24 (puzzles 900–999, 100개) | Game24 (puzzles 901–1000, 100개) |
| 온도 | 0.7 | 0.7 |
| 시스템 프롬프트 | `"You are a concise assistant. Follow the output format shown in the examples exactly. Do not add explanations, numbered lists, markdown, or any text beyond what the format requires."` | 없음 (논문에 언급 없음) |

> **주의**: 시스템 프롬프트는 gpt-4o-mini의 markdown/LaTeX 출력을 방지하기 위해 추가된 것으로, 논문 원본 조건과 다르다. 이로 인해 결과 차이가 발생할 수 있음.

---

## 재현 대상 Figure / Table

| 항목 | 설명 |
|------|------|
| **Table 2** | IO / CoT / CoT-SC / ToT (b=1, b=5) / IO best of 100 / CoT best of 100 성공률 |
| **Figure 3(a)** | nodes visited 대비 성공률 (IO/CoT best of k vs ToT b=1~5) |
| **Figure 3(b)** | step별 실패율 (CoT vs ToT b=5) |
| **Table 7** | 방법별 토큰 수 및 비용 |

---

## 실험 목록

### 1. IO — 단일 샘플 (Table 2: "IO prompt")

100문제 × 1회 샘플, 성공률 평균.

```bash
python run.py \
  --task game24 \
  --backend gpt-4o-mini \
  --naive_run \
  --prompt_sample standard \
  --n_generate_sample 1 \
  --task_start_index 900 \
  --task_end_index 1000
```

---

### 2. IO — best of 100 (Table 2: "IO best of 100", Figure 3(a))

100문제 × 100회 샘플, 문제당 하나라도 성공하면 성공으로 집계.

```bash
python run.py \
  --task game24 \
  --backend gpt-4o-mini \
  --naive_run \
  --prompt_sample standard \
  --n_generate_sample 100 \
  --task_start_index 900 \
  --task_end_index 1000
```

---

### 3. CoT — 단일 샘플 (Table 2: "CoT prompt", Figure 3(b))

100문제 × 1회 샘플, 성공률 평균.  
step별 실패율 분석(Figure 3(b))은 이 로그를 사용.

```bash
python run.py \
  --task game24 \
  --backend gpt-4o-mini \
  --naive_run \
  --prompt_sample cot \
  --n_generate_sample 1 \
  --task_start_index 900 \
  --task_end_index 1000
```

---

### 4. CoT-SC (Table 2: "CoT-SC (k=100)")

100문제 × 100회 샘플 → majority vote.

```bash
python run.py \
  --task game24 \
  --backend gpt-4o-mini \
  --naive_run \
  --prompt_sample cot \
  --n_generate_sample 100 \
  --task_start_index 900 \
  --task_end_index 1000
```

> 이 로그에서 CoT-SC(majority vote, 실험 4)와 CoT best of 100(any-correct, 실험 5)을 모두 집계 가능.

---

### 5. CoT — best of 100 (Table 2: "CoT best of 100", Figure 3(a))

실험 4와 동일한 로그에서 any-correct 기준으로 재집계.  
별도 실행 불필요.

---

### 6. ToT (b=5) — 논문 주요 결과 (Table 2, Figure 3(a)(b), Table 7)

```bash
python run.py \
  --task game24 \
  --backend gpt-4o-mini \
  --method_generate propose \
  --n_generate_sample 1 \
  --method_evaluate value \
  --n_evaluate_sample 3 \
  --method_select greedy \
  --n_select_sample 5 \
  --task_start_index 900 \
  --task_end_index 1000
```

---

### 7. ToT (b=1) (Table 2: "ToT (b=1)", Figure 3(a))

```bash
python run.py \
  --task game24 \
  --backend gpt-4o-mini \
  --method_generate propose \
  --n_generate_sample 1 \
  --method_evaluate value \
  --n_evaluate_sample 3 \
  --method_select greedy \
  --n_select_sample 1 \
  --task_start_index 900 \
  --task_end_index 1000
```

---

### 8. ToT (b=2, 3, 4) — Figure 3(a) 곡선 완성용

Figure 3(a)의 ToT 곡선은 b=1~5 5개 데이터포인트가 필요.  
실험 6, 7 외에 b=2, 3, 4도 추가 실행.

```bash
# b=2
python run.py ... --n_select_sample 2 ...
# b=3
python run.py ... --n_select_sample 3 ...
# b=4
python run.py ... --n_select_sample 4 ...
```

---

## 추가 실험 (논문 외)

> 논문 발표(2023) 이후 등장한 OpenAI reasoning 모델을 활용한 확장 실험.  
> 핵심 질문: **"외부 구조(ToT) 없이 내부 추론 모델만으로 ToT를 이길 수 있는가?"**  
> 결정 근거: ADR-0005 참조.

### 9. o4-mini — IO×1 (추가 실험)

o4-mini는 답변 전 내부 chain-of-thought를 수행하는 reasoning 모델이다.  
단일 IO 프롬프트만으로 GPT-4o mini ToT b=5와 비교한다.

| 항목 | 값 |
|------|-----|
| 모델 | `o4-mini` |
| 방법 | IO (standard prompt, 단일 샘플) |
| 비교 대상 | GPT-4o mini ToT b=5 |
| 예상 비용 | ~$0.40 |

> **o1을 쓰지 않는 이유**: o1은 비용 ~$12, n>1 미지원. o4-mini는 ~$0.40, n>1 지원, reasoning tokens 효율 우수 (832 vs 2000+).

```bash
# models.py에 o4-mini 분기 추가 후 실행
python run.py \
  --task game24 \
  --backend o4-mini \
  --naive_run \
  --prompt_sample standard \
  --n_generate_sample 1 \
  --task_start_index 900 \
  --task_end_index 1000
```

---

## 논문 GPT-4 baseline (비교 기준)

| 방법 | 성공률 (Table 2) |
|------|----------------|
| IO prompt | 7.3% |
| CoT prompt | 4.0% |
| CoT-SC (k=100) | 9.0% |
| ToT (b=1) | 45% |
| ToT (b=5) | **74%** |
| IO + Refine (k=10) | 27% |
| IO best of 100 | 33% |
| CoT best of 100 | 49% |

출처: Yao et al. (2023) Table 2

---

## 비용 추정 (gpt-4o-mini 기준)

| 실험 | API 호출 수 | 예상 비용 |
|------|-----------|---------|
| IO × 1 | 100회 | ~$0.01 |
| IO × 100 | 10,000회 | ~$1.0 |
| CoT × 1 | 100회 | ~$0.01 |
| CoT × 100 | 10,000회 | ~$1.0 |
| ToT (b=5) | ~6,600회 | ~$0.70 |
| ToT (b=1~4) | ~5,280회 | ~$0.56 |
| **합계** | | **~$3.3** |

---

## 진행 상황

- [x] 실험 1: IO 단일 샘플
- [x] 실험 2: IO × 100 (IO best of 100)
- [x] 실험 3: CoT 단일 샘플
- [ ] 실험 4/5: CoT × 100 (CoT best of 100 + CoT-SC 겸용)
- [ ] 실험 6: ToT (b=5)
- [ ] 실험 7: ToT (b=1)
- [ ] 실험 8: ToT (b=2, 3, 4)
- [x] 실험 9: o4-mini IO×1 (추가 실험) — 76%
- [ ] Table 2 집계
- [ ] Figure 3(a)(b) 데이터 집계
- [ ] Table 7 비용 집계