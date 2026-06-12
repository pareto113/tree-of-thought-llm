# EXP-001: qwen2.5:14b-instruct vs GPT-4 공정 비교 (CoT baseline)

> 작성일: 2026-06-04  
> 브랜치: `feature/ollama-qwen`  
> 상태: 계획 중

---

## 배경

앞서 수행한 naive CoT 비교 실험에서 GPT-4가 3/3 (100%), qwen이 0/3 (0%)라는
극단적인 결과가 나왔으나, 실험 조건이 동일하지 않았다.

| 항목 | GPT-4 로그 | qwen 로그 |
|------|-----------|---------|
| n_generate_sample | **100** | **1** |
| 퍼즐 수 | 100 | 3 |

GPT-4는 퍼즐당 100번 시도해 최선을 고른 반면, qwen은 단 1번만 시도했다.
이 조건 차이가 결과에 결정적 영향을 줬을 가능성이 높아 재실험이 필요하다.

---

## 목적

동일한 `n_generate_sample`과 퍼즐 수 조건에서 두 모델의 CoT 정확도를 비교해,
qwen2.5:14b-instruct가 실질적으로 GPT-4 대비 얼마나 열세인지 측정한다.

---

## 실험 설계

### Phase 1 — 검증 실험 (소규모)

| 항목 | 값 |
|------|----|
| 퍼즐 범위 | 900–910 (10개) |
| n_generate_sample | 10 |
| prompt_sample | cot |
| 목적 | 조건 통일 후 결과 방향 확인, ETA 측정 |

```bash
source .venv-ollama/bin/activate
python run.py \
    --task game24 \
    --task_start_index 900 --task_end_index 910 \
    --naive_run --prompt_sample cot \
    --n_generate_sample 10
```

**Phase 1 판단 기준**
- cnt_any ≥ 30% → Phase 2 진행
- cnt_any < 30% → 모델 한계로 판단, 실험 중단 검토

---

### Phase 2 — 본실험 (GPT-4 원본과 동일 규모)

| 항목 | 값 |
|------|----|
| 퍼즐 범위 | 900–1000 (**100개**) |
| n_generate_sample | 10 |
| prompt_sample | cot |
| 목적 | GPT-4 원본 로그와 정면 비교 |

```bash
python run.py \
    --task game24 \
    --task_start_index 900 --task_end_index 1000 \
    --naive_run --prompt_sample cot \
    --n_generate_sample 10
```

> GPT-4 원본은 n=100이므로 n=10으로도 여전히 불리한 조건임.
> 단, n=100은 속도상 현실적으로 어려워 n=10을 타협점으로 선택.

---

## 비교 대상 로그

| 모델 | 로그 파일 | n | 퍼즐 수 |
|------|----------|:-:|:-------:|
| GPT-4 (원본) | `gpt-4_0.7_naive_cot_sample_100_start900_end1000.json` | 100 | 100 |
| qwen (Phase 1) | `qwen2.5:14b-instruct_0.7_naive_cot_sample_10_start900_end910.json` | 10 | 10 |
| qwen (Phase 2) | `qwen2.5:14b-instruct_0.7_naive_cot_sample_10_start900_end1000.json` | 10 | 100 |

---

## 측정 지표

| 지표 | 설명 |
|------|------|
| `cnt_any` | 퍼즐당 n개 답안 중 1개 이상 정답인 비율 (주 지표) |
| `cnt_avg` | 퍼즐당 평균 정답률 |
| 소요 시간 | Phase 1 ETA로 Phase 2 예상 시간 산출 |

---

## 예상 소요 시간

Phase 1 실험 후 ETA 로그를 기반으로 Phase 2 시간을 추산한다.

| 항목 | 추산 기준 |
|------|---------|
| Phase 1 (10 puzzles × n=10) | 실측 후 확인 |
| Phase 2 (100 puzzles × n=10) | Phase 1 avg_per_puzzle × 100 |

---

## 결과 기록

실험 완료 후 아래 항목을 채운다.

### Phase 1 결과
- 실행일: 
- 소요 시간: 
- cnt_any: 
- cnt_avg: 
- avg_per_puzzle: 
- Phase 2 예상 시간: 
- Phase 2 진행 여부: 

### Phase 2 결과
- 실행일: 
- 소요 시간: 
- cnt_any: 
- cnt_avg: 
- GPT-4 대비: 
- 평가 로그: `logs/eval/qwen2.5:14b-instruct_0.7_naive_cot_sample_10_start900_end1000_eval.json`
