# Tree of Thoughts (ToT) — 프로젝트 구조 분석

> 원본: Yao et al. (2023), "Tree of Thoughts: Deliberate Problem Solving with Large Language Models" (arXiv:2305.10601)  
> 포크 기준 커밋: `8050e67` (gpt-4o 옵션 추가 포함)

---

## 1. 개요

Tree of Thoughts(ToT)는 LLM이 문제를 풀 때 **단일 경로의 토큰 스트림** 대신 **트리 구조로 여러 사고 경로를 탐색**하게 하는 프레임워크다. 각 중간 "사고(thought)"를 독립적으로 평가·선택하여 BFS/DFS로 탐색한다.

```
입력(x)
  └─ 사고 후보 생성 (generate)
       ├─ 후보 평가 (evaluate: value / vote)
       └─ 상위 후보 선택 (select: greedy / sample)
            └─ 다음 스텝 반복 → 최종 출력(y)
```

---

## 2. 디렉터리 구조

```
tree-of-thought-llm/
├── run.py                          # CLI 진입점 (실험 루프)
├── setup.py                        # PyPI 패키징 설정
├── requirements.txt                # 의존성 목록
├── MANIFEST.in
├── pyproject.toml
│
├── src/tot/                        # 핵심 패키지
│   ├── __init__.py
│   ├── models.py                   # OpenAI API 래퍼 (gpt / chatgpt / gpt_usage)
│   │
│   ├── methods/
│   │   └── bfs.py                  # ToT+BFS 및 naive 풀이 알고리즘
│   │
│   ├── tasks/
│   │   ├── __init__.py             # get_task() 팩토리
│   │   ├── base.py                 # Task 추상 기반 클래스
│   │   ├── game24.py               # Game of 24 태스크
│   │   ├── text.py                 # Creative Writing 태스크
│   │   └── crosswords.py           # Mini Crosswords 태스크 + 환경
│   │
│   ├── prompts/
│   │   ├── game24.py               # Game24용 프롬프트 템플릿
│   │   ├── text.py                 # Writing용 프롬프트 템플릿
│   │   └── crosswords.py           # Crosswords용 프롬프트 템플릿
│   │
│   └── data/
│       ├── 24/24.csv               # 1,362개 Game of 24 퍼즐
│       ├── text/data_100_random_text.txt  # 100개 문장 집합
│       └── crosswords/
│           ├── mini0505.json       # 전체 미니 크로스워드 데이터
│           └── mini0505_0_100_5.json
│
├── scripts/                        # 실험 재현용 셸 스크립트
│   ├── game24/{bfs,cot_sampling,standard_sampling}.sh
│   ├── text/{bfs,cot_sampling,standard_sampling}.sh
│   └── crosswords/{cot_sampling,standard_sampling}.sh
│       search_crosswords-dfs.ipynb # DFS 탐색 (Jupyter)
│
└── logs/                           # 논문 실험 결과 JSON
    ├── game24/
    ├── text/
    └── crosswords/
```

---

## 3. 핵심 모듈 상세

### 3.1 `src/tot/models.py` — LLM 인터페이스

| 함수 | 역할 |
|------|------|
| `gpt(prompt, ...)` | 단일 프롬프트 → ChatCompletion, 결과 리스트 반환 |
| `chatgpt(messages, ...)` | 배치 처리 (n>20이면 20개씩 분할) + 토큰 누적 |
| `completions_with_backoff(...)` | `@backoff.expo` 데코레이터로 OpenAI 오류 재시도 |
| `gpt_usage(backend)` | 누적 토큰·비용 반환 |

**지원 모델**: `gpt-4`, `gpt-3.5-turbo`, `gpt-4o` (포크에서 추가)  
**비용 단가** (하드코딩): gpt-4 $0.03/0.06K, gpt-3.5-turbo $0.0015/0.002K, gpt-4o $0.01/0.0025K  
**주의**: `openai==0.27.7` (구버전 API — `openai.ChatCompletion.create` 방식)

---

### 3.2 `src/tot/methods/bfs.py` — 탐색 알고리즘

#### `solve(args, task, idx)` — ToT + BFS

```
for step in range(task.steps):
    1. 생성(generate)
       - sample  : get_samples()  → standard / cot 프롬프트로 독립 샘플링
       - propose : get_proposals() → 순차적 다음 스텝 제안
    2. 평가(evaluate)
       - value : get_values() → 각 후보를 개별 점수화
       - vote  : get_votes()  → 후보들을 함께 비교해 투표
    3. 선택(select)
       - greedy : 상위 n_select_sample개
       - sample : 점수 비례 확률 샘플링
```

**값 캐싱**: `task.value_cache`에 프롬프트 → 값 매핑을 저장해 중복 API 호출 방지

#### `naive_solve(args, task, idx)` — IO / CoT 베이스라인

트리 탐색 없이 단일 `get_samples()` 호출 후 바로 반환.

---

### 3.3 `src/tot/tasks/` — 태스크 레이어

#### 추상 기반 클래스 `Task` (base.py)

```python
class Task:
    def __len__(self) -> int: ...
    def get_input(self, idx: int) -> str: ...
    def test_output(self, idx: int, output: str): ...
```

각 태스크는 추가로 `*_prompt_wrap()` / `*_outputs_unwrap()` 메서드를 구현한다.

---

#### `Game24Task` (game24.py)

| 속성/메서드 | 내용 |
|-------------|------|
| 데이터 | `24.csv` (1,362 퍼즐, idx 900~999가 논문 실험 범위) |
| `steps` | 4 (3번의 연산 + 최종 답 확인) |
| `stops` | `['\n'] * 4` |
| `test_output` | sympy로 수식 계산 → 결과가 24이면 r=1 |
| `propose_prompt_wrap` | 현재 남은 숫자 기반으로 다음 연산 제안 요청 |
| `value_prompt_wrap` | 중간 단계: 남은 숫자로 24 도달 가능성 평가 / 최종 단계: 식 검증 |
| `value_outputs_unwrap` | `impossible:0.001`, `likely:1`, `sure:20` 매핑 후 합산 |

**탐색 전략**: `propose` + `value` + `greedy` (n_evaluate=3, n_select=5)

---

#### `TextTask` (text.py)

| 속성/메서드 | 내용 |
|-------------|------|
| 데이터 | 100개 랜덤 문장 (각 문장이 4개 문단 마지막 문장이 되어야 함) |
| `steps` | 2 (`Plan` 단계 → `Passage` 단계) |
| `stops` | `['\nPassage:\n', None]` |
| `test_output` | GPT-4를 심사위원으로 사용 → 일관성 점수 1~10 평균 |
| `vote_prompt_wrap` | 여러 후보 글을 비교해 최선 선택 |
| `compare_prompt_wrap` | 두 글 직접 비교 (compare 방식, 실험에선 미사용) |

**탐색 전략**: `sample(cot)` + `vote` + `greedy` (n_generate=5, n_evaluate=5, n_select=1)

---

#### `MiniCrosswordsTask` + `MiniCrosswordsEnv` (crosswords.py)

`MiniCrosswordsEnv`는 5×5 크로스워드 **게임 환경**을 구현한다 (OpenAI Gym 스타일).

| MiniCrosswordsEnv 메서드 | 내용 |
|--------------------------|------|
| `reset(idx)` | 퍼즐 초기화, 보드 상태 반환 |
| `step(action)` | `"h1. apple"` 형식 액션 → 보드 업데이트, 보상 반환 |
| `render()` | 현재 보드 + 미입력/입력/변경 단어 목록 출력 |
| `prompt_status()` | GPT에게 각 단어 후보의 적합성 평가 요청 (sure/maybe/impossible) |

| MiniCrosswordsTask 속성 | 내용 |
|-------------------------|------|
| `steps` | 10 (가로5 + 세로5 단어) |
| `propose_outputs_unwrap` | 신뢰도(`certain`/`high`/`medium`/`low`) 기반 점수로 제안 순위화 |
| `evaluate` | 현재 보드 각 단어의 가능성 평가 |

**탐색 전략**: BFS 대신 **DFS** (`search_crosswords-dfs.ipynb`에서 구현)

---

### 3.4 `src/tot/prompts/` — 프롬프트 템플릿

각 태스크별 Python 파일에 프롬프트 문자열을 상수로 정의한다.

| 프롬프트 종류 | 설명 |
|---------------|------|
| `standard_prompt` | 직접 답변 요청 (IO 방식) |
| `cot_prompt` | 단계별 추론 포함 (Chain-of-Thought) |
| `propose_prompt` | 다음 가능한 스텝들을 나열 |
| `value_prompt` | 현재 상태가 목표에 도달 가능한지 평가 |
| `vote_prompt` | 여러 후보 중 최선 선택 |

모든 프롬프트는 Few-shot 예시를 포함하며 `{input}` 플레이스홀더를 사용한다.

---

### 3.5 `run.py` — 실험 CLI

```bash
python run.py \
  --backend gpt-4 \
  --temperature 0.7 \
  --task game24 \
  --task_start_index 900 \
  --task_end_index 1000 \
  --method_generate propose \
  --method_evaluate value \
  --method_select greedy \
  --n_generate_sample 1 \
  --n_evaluate_sample 3 \
  --n_select_sample 5
```

결과는 `logs/{task}/{backend}_{temp}_{method설정}_{범위}.json`으로 저장된다.  
`--naive_run` 플래그를 주면 `naive_solve()`로 실행 (베이스라인 IO/CoT).

---

## 4. 데이터 흐름 요약

```
run.py
  │
  ├─ get_task(name)          → Task 인스턴스 생성
  │
  └─ solve(args, task, idx)  (bfs.py)
       │
       ├─ task.get_input(idx)
       │
       ├─[loop: steps]
       │   ├─ generate:  get_proposals() / get_samples()
       │   │              └─ gpt(prompt, n=...) → models.py → OpenAI API
       │   ├─ evaluate:  get_values() / get_votes()
       │   │              └─ gpt(prompt, n=...) → (with value_cache)
       │   └─ select:    greedy / sample
       │
       └─ task.test_output(idx, y) → 정답 검증 → logs/ 저장
```

---

## 5. 논문 vs. 구현 대응표

| 논문 개념 | 구현 위치 |
|-----------|-----------|
| Thought Generator (G) | `get_proposals()` / `get_samples()` in bfs.py |
| State Evaluator (V) | `get_values()` / `get_votes()` in bfs.py |
| BFS(b=beam) | `solve()` — `n_select_sample`이 beam width b |
| DFS | `search_crosswords-dfs.ipynb` |
| IO baseline | `naive_solve()` with `standard` prompt |
| CoT baseline | `naive_solve()` with `cot` prompt |

---

## 6. 포크에서 추가된 변경 사항

| 변경 | 파일 | 내용 |
|------|------|------|
| gpt-4o 지원 | `models.py`, `run.py` | `gpt-4o` 백엔드 추가, 토큰 비용 단가 하드코딩 |
| API 호환성 수정 | `models.py` | 구버전 `openai==0.27.7` 유지 (신버전은 호환 안 됨) |

---

## 7. 확장 포인트 (새 태스크 추가 방법)

1. `src/tot/tasks/` 에 `MyTask(Task)` 클래스 작성
   - `get_input()`, `test_output()` 필수
   - 필요한 `*_prompt_wrap()` / `*_outputs_unwrap()` 구현
2. `src/tot/tasks/__init__.py`의 `get_task()`에 분기 추가
3. `src/tot/prompts/`에 태스크 전용 프롬프트 파일 추가
4. `src/tot/data/`에 데이터 파일 추가
5. `scripts/`에 실험 스크립트 작성

---

## 8. 의존성

| 패키지 | 역할 |
|--------|------|
| `openai==0.27.7` | ChatCompletion API (구버전 인터페이스) |
| `backoff==2.2.1` | API 오류 시 지수 백오프 재시도 |
| `sympy==1.12` | Game24 정답 수식 검증 |
| `pandas==2.0.3` | 24.csv 로딩 |
| `numpy==1.24.3` | sample 선택 확률 계산 |
