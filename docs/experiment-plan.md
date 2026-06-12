# GPT-4o mini 적용 실험 계획 — Game24

## 목적

Yao et al. (2023) Tree of Thoughts 논문의 Game24 실험을 GPT-4o mini에 적용한다.  
GPT-4 대비 GPT-4o mini에서 IO / CoT / ToT 방법론의 성능 차이를 비교한다.  
(재현 실험이 아닌 **적용 실험** — ADR-0001 참조)

---

## 실험 조건

| 항목 | 값 |
|------|-----|
| 모델 | `gpt-4o-mini` |
| 태스크 | Game24 (puzzles 900–999, 100개) |
| 온도 | 0.7 |
| 시스템 프롬프트 | 없음 (ADR-0002 참조) |

---

## 실험 목록

### 1. IO (Input-Output, Naive Standard)

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

- 로그 파일: `logs/game24/gpt-4o-mini_0.7_naive_standard_sample_100_start900_end1000.json`

### 2. CoT (Chain-of-Thought, Naive CoT)

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

- 로그 파일: `logs/game24/gpt-4o-mini_0.7_naive_cot_sample_100_start900_end1000.json`

### 3. ToT (Tree of Thoughts, BFS)

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

- 로그 파일: `logs/game24/gpt-4o-mini_0.7_propose1_value3_greedy5_start900_end1000.json`

---

## 논문 GPT-4 baseline (비교 기준)

| 방법 | cnt_any | cnt_avg |
|------|---------|---------|
| IO   | 33%     | 0.073   |
| CoT  | 49%     | 0.040   |
| ToT  | 69%     | 0.238   |

출처: `logs/eval/gpt-4_0.7_*_eval.json` (논문 저자 제공 로그)

---

## 평가

각 실험 완료 후:

```bash
python scripts/evaluate_log.py <로그파일> --save
```

결과는 `logs/eval/<파일명>_eval.json`에 저장되며 `meta`, `accuracy`, `format`, `usage` 필드를 포함한다.

---

## 진행 상황

- [ ] IO 실험 실행
- [ ] CoT 실험 실행
- [ ] ToT 실험 실행
- [ ] 각 실험 eval 생성
