# 2026-06-04 세션 요약

---

## 한 일

### 1. 프로젝트 분석 및 문서화
- 전체 코드 구조 분석 → [`ARCHITECTURE.md`](../../ARCHITECTURE.md)
- API 비용 추산 (GPT-4 실측 로그 기반) → [`notes/api-cost-estimate.md`](../api-cost-estimate.md)

### 2. 로컬 모델 적용 가능성 분석
- **qwen3.5:9b (thinking 모델)** 테스트 → [`notes/thinking-model-vs-gpt4o.md`](../thinking-model-vs-gpt4o.md)
  - thinking ON: value 1회에 ~114초, 사실상 실용 불가
  - thinking OFF: 빠르지만 propose 형식 완전 이탈 (마크다운 출력)
- **qwen2.5:14b-instruct** 테스트 → [`notes/qwen2.5-14b-instruct-analysis.md`](../qwen2.5-14b-instruct-analysis.md)
  - system prompt 없이: 형식 이탈 (파싱 실패)
  - system prompt 추가 후: propose 형식 준수, value 파싱 ~80%
  - propose `left:` 수학 오류 ~43% 잔존

### 3. 브랜치 및 환경 구성

| 브랜치 | 모델 | venv | 주요 변경 |
|--------|------|------|---------|
| `feature/ollama-qwen` | qwen2.5:14b-instruct | `.venv-ollama` | models.py → Ollama API + system prompt |
| `feature/gpt4o-mini` | GPT-4o mini | `.venv-gpt4o` | models.py → openai v1.x 업그레이드 |

- `.gitignore`에 `.venv-*` 추가
- `README.md`에 브랜치별 사용법 추가

### 4. 평가 도구 구축
- [`scripts/evaluate_log.py`](../../scripts/evaluate_log.py) 작성
  - 형식 평가: propose 형식 준수율, 수학 정확도, value 파싱 성공률
  - 정확도 평가: cnt_avg, cnt_any
  - `--save` 옵션으로 `logs/eval/`에 JSON 저장
- `logs/eval/` 디렉터리 신설 (raw log와 분석 결과 분리)

### 5. 기존 로그 평가 및 비교

**형식 준수율 비교 (GPT-4 vs qwen2.5:14b, ToT 기준)**

| 모델 | Propose 형식 준수율 | Value 파싱 성공률 | cnt_any |
|------|:------------------:|:-----------------:|:-------:|
| GPT-4 (100 puzzles) | 89.2% | 74.1% | 69% |
| qwen2.5:14b (3 puzzles) | 85.9% | 78.4% | 33% |

→ 형식 측면에서 qwen이 GPT-4 대비 크게 뒤처지지 않음. 형식이 병목이 아님.

**정확도 비교 (공정 조건 미충족 상태)**

| 방식 | GPT-4 (n=100) | qwen (n=1) |
|------|:------------:|:-----------:|
| IO (standard) | 1/3 (33%) | 1/3 (33%) |
| CoT | 3/3 (100%) | 0/3 (0%) |

→ n_generate_sample 차이(100 vs 1)가 결과에 결정적 영향. 공정 비교 불가.

### 6. run.py ETA 기능 추가
- 퍼즐 완료 시마다 `puzzle / avg / elapsed / ETA` 실시간 출력
- 두 브랜치 모두 적용

### 7. 실험 계획 수립
- [`notes/experiments/exp_001_qwen_cot_fair_comparison.md`](../experiments/exp_001_qwen_cot_fair_comparison.md)
  - Phase 1: 10 puzzles × CoT × n=10 (검증 + ETA 측정)
  - Phase 2: 100 puzzles × CoT × n=10 (GPT-4 원본과 비교)

---

## 현재 상태

- **Phase 1 실험 진행 중** (콘솔에서 실행)
  ```bash
  python run.py --task game24 \
      --task_start_index 900 --task_end_index 910 \
      --naive_run --prompt_sample cot --n_generate_sample 10
  ```
- 결과 완료 후 `evaluate_log.py --save`로 평가 → Phase 2 진행 여부 결정

---

## 다음 할 일

- [ ] Phase 1 결과 평가 및 ETA 기반 Phase 2 시간 추산
- [ ] Phase 1 cnt_any ≥ 30%이면 Phase 2 (100 puzzles) 실행
- [ ] Phase 2 완료 후 GPT-4 원본 로그와 정면 비교
- [ ] 필요 시 `feature/gpt4o-mini` 브랜치 실험 병행 검토

---

## 생성된 파일 목록

| 파일 | 설명 |
|------|------|
| `ARCHITECTURE.md` | 프로젝트 전체 구조 분석 |
| `notes/api-cost-estimate.md` | 모델별 API 비용 추산 (GPT-4/4o/4o-mini/Haiku 4.5) |
| `notes/thinking-model-vs-gpt4o.md` | Thinking 모델 vs GPT-4o 특성 비교 |
| `notes/qwen2.5-14b-instruct-analysis.md` | qwen2.5:14b ToT 적용 분석 |
| `notes/experiments/exp_001_qwen_cot_fair_comparison.md` | EXP-001 실험 계획서 |
| `notes/0604/session-summary.md` | 본 문서 |
| `scripts/evaluate_log.py` | 실험 로그 형식·정확도 평가 스크립트 |
| `logs/eval/*.json` | 평가 결과 6개 |
