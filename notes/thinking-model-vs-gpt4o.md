# Thinking 모델 vs GPT-4o — 특징 비교 및 ToT 적용 시 예상 결과

> 실측 환경: qwen3.5:9b (Q4_K_M, 9.7B params) on Ollama / 로컬 추론  
> 비교 기준: GPT-4o (OpenAI API)  
> 측정일: 2026-06-03

---

## 1. Thinking 모델이란

일반 LLM은 입력 프롬프트를 받아 즉시 응답 토큰을 생성한다.  
Thinking 모델(= 추론 모델, reasoning model)은 응답 전에 **내부 추론 단계(chain-of-thought)를 명시적으로 생성**한다.

```
일반 모델:  [프롬프트] → [응답]

Thinking 모델: [프롬프트] → [<think>내부 추론...</think>] → [응답]
```

추론 단계의 토큰은 사용자에게 보이지 않거나(OpenAI o1) Ollama처럼 별도 필드로 분리된다(`thinking` 필드).  
대표 모델: OpenAI o1/o3, DeepSeek-R1, Qwen3 시리즈(qwen3.5:9b 포함).

---

## 2. GPT-4o와의 핵심 차이

| 항목 | GPT-4o | qwen3.5:9b (thinking 모드) |
|------|--------|---------------------------|
| 응답 방식 | 즉시 토큰 생성 | 내부 추론 후 응답 생성 |
| 추론 토큰 | 없음 (잠재적으로 내재화) | 명시적으로 생성 (별도 필드) |
| 파라미터 수 | ~200B (추정) | 9.7B |
| 양자화 | 없음 (FP16/BF16) | Q4_K_M (4-bit 양자화) |
| 추론 위치 | OpenAI 서버 (GPU 클러스터) | 로컬 (단일 GPU/CPU) |
| 지시 따르기 (instruction following) | 매우 강함 | 중간 수준 |

---

## 3. 실측: ToT 프롬프트에서 두 모드 비교

### 3-1. Value 프롬프트 (sure/likely/impossible 판별)

```
프롬프트: "Evaluate if given numbers can reach 24 (sure/likely/impossible) ... 5 6 6"
정답:     "sure" (5 * 6 - 6 = 24)
```

| 모드 | 생성 토큰 수 | 소요 시간 | 출력 |
|------|:-----------:|:--------:|------|
| **thinking ON** | **4,801 tokens** | **113,875ms (약 1분 54초)** | `5 * 6 - 6 = 24\nsure` |
| thinking OFF | **2 tokens** | **26ms** | `sure` |

thinking 모드는 4,800개의 내부 추론 토큰을 소비한 뒤에야 단 두 토큰(`sure`)을 출력했다.

thinking 모드의 내부 추론 일부:
```
Thinking Process:
1. Analyze the Request: The user wants me to evaluate if given numbers can reach 24...
2. Analyze the Input: Input: "5 6 6" / Goal: Reach 24 using 5, 6, 6.
   Operation constraints: Usually standard 24 Game rules allow...
   - Example 1: 10 + 14 = 24 → sure...
```

---

### 3-2. Propose 프롬프트 (다음 스텝 제안)

```
프롬프트: "Input: 4 5 6 10\nPossible next steps:\n"
기대 형식: "4 + 5 = 9 (left: 6 9 10)\n..."  ← 파서가 \n으로 분리해서 사용
```

| 모드 | 생성 토큰 수 | 소요 시간 | 형식 준수 |
|------|:-----------:|:--------:|:--------:|
| **thinking ON** | **8,497 tokens** | **204,750ms (약 3분 25초)** | ✅ 정확히 준수 |
| thinking OFF | 868 tokens | 20,649ms | ❌ 마크다운 형식으로 이탈 |

**thinking OFF 실제 출력 (문제):**
```markdown
*   **4 + 5 = 9** (left: **9 6 10**)
*   **5 + 6 = 11** (left: **4 11 10**)
...
If you need just the format matching...
```

코드의 파서 `gpt(propose_prompt)[0].split('\n')`는 이런 마크다운 형식을 처리할 수 없다.

---

## 4. 왜 다른 결과가 나타날 가능성이 높은가

### 4-1. 파싱 실패 (즉각적 오류)

`bfs.py`의 핵심 파서들은 GPT-4의 깔끔한 출력을 전제로 설계됐다.

```python
# get_proposals() in bfs.py:28
proposals = gpt(propose_prompt, n=1, stop=None)[0].split('\n')
```

thinking OFF 모드의 qwen3.5:9b는 마크다운 불릿(`* **...** (left: ...)`), 설명 문단, 소제목 등을 추가로 생성한다. `split('\n')`으로 나눠도 파서가 기대하는 `"X op Y = Z (left: ...)"` 형식과 맞지 않아 유효한 후보를 찾지 못한다.

결과: `get_proposals()`가 빈 리스트 또는 쓸모없는 후보만 반환 → BFS가 즉시 실패.

### 4-2. Value 점수의 신뢰도 저하

```python
# game24.py:90
value_map = {'impossible': 0.001, 'likely': 1, 'sure': 20}
value = sum(value * value_names.count(name) for name, value in value_map.items())
```

파서는 응답의 **마지막 줄**에서 `impossible/likely/sure` 단어를 추출한다.  
9B 모델은 확신 수준 판단에서 GPT-4보다 오판율이 높고, 형식을 벗어나면 파싱 자체가 실패해 value가 0으로 처리된다.

올바른 상태를 "impossible"로 잘못 평가하면 BFS에서 좋은 경로가 조기에 제거된다.

### 4-3. Thinking 모드의 "이중 추론" 문제

ToT는 외부에서 LLM에게 단계적 추론을 지시하는 프레임워크다.  
Thinking 모델은 이미 내부적으로 추론을 수행한다.

```
ToT 의도: "모델아, 이 숫자들로 24를 만들 수 있는지 생각해봐"
Thinking 모델 내부: "이 숫자들로 24를 만들 수 있는지 생각해봐...
                     (스스로 4,800 토큰 추론 후)
                     sure"
```

내부 추론이 ToT의 value/vote 메커니즘과 의도적으로 분리되지 않아, 모델이 자체 판단을 내리고 프롬프트의 Few-shot 패턴을 따르는 대신 자기 방식으로 답하려는 경향이 생긴다.

### 4-4. 파라미터 규모 차이의 영향

| 능력 | GPT-4o (~200B) | qwen3.5:9b (9.7B, 4-bit) |
|------|:--------------:|:------------------------:|
| 지시 정확 이행 | 매우 강함 | 보통 |
| Few-shot 형식 준수 | 거의 완벽 | 가끔 이탈 |
| 수학적 추론 | 강함 | 중간 |
| 다단계 계획 | 강함 | 제한적 |

Q4_K_M 양자화는 FP16 대비 정보 손실이 발생하며, 특히 형식 일관성과 다단계 추론에서 차이가 두드러진다.

---

## 5. 왜 느려지는가

### 5-1. Thinking 토큰의 비대한 오버헤드

Value 한 번 호출에 4,801 토큰 생성 → Game24 ToT 1개 퍼즐의 최대 호출 구조:

```
4 steps × (propose 1회 + value 3회 × 최대 5개 후보)
= 최대 64회 API 호출

value 호출 최대 60회 × 4,801 tokens = 288,060 thinking tokens
                                      + 실제 응답 ~60 tokens
```

GPT-4o는 value 한 번에 수십 ms / qwen3.5:9b thinking 모드는 **113,875ms (약 2분)**

따라서:
```
GPT-4 Game24 100 puzzles: ~실측 $74.51, 수십 분 소요
qwen3.5:9b thinking ON:  무료지만 100 puzzles × 64 calls × ~2분 = 최대 213시간(!)
```

### 5-2. 로컬 추론 속도

| 환경 | 토큰 생성 속도 |
|------|:-------------:|
| OpenAI GPT-4o 서버 | ~100–200 tokens/sec (병렬 GPU 클러스터) |
| 로컬 qwen3.5:9b | ~42 tokens/sec (실측: 8,497 tokens / 204.75s) |

OpenAI 대비 약 3–5배 느린 생성 속도 + thinking 토큰 오버헤드가 결합된다.

---

## 6. 모드별 전략 정리

| 모드 | 속도 | 형식 준수 | 정확도 | ToT 적합성 |
|------|:----:|:--------:|:------:|:----------:|
| qwen3.5:9b, thinking ON | ❌ 매우 느림 | ✅ 정확 | ✅ 높음 | ⚠️ 실용 불가 (속도) |
| qwen3.5:9b, thinking OFF | ✅ 빠름 | ❌ 형식 이탈 | ⚠️ 보통 | ❌ 파싱 실패 |
| qwen2.5:14b-instruct | ✅ 빠름 | ✅ 중간 | ⚠️ 보통 | ⚠️ 시도해볼 만함 |
| GPT-4o | ✅ 빠름 | ✅ 완벽 | ✅ 높음 | ✅ 원본 설계 대상 |

**실용적 결론:**  
qwen3.5:9b로 ToT를 돌리려면 두 가지 중 하나가 필요하다.
1. **프롬프트에 출력 형식을 더 엄격하게 명시**하고 thinking OFF로 실행 → 형식 이탈 완화
2. **파서를 유연하게 수정**해서 마크다운/부연설명이 섞인 출력에서도 유효한 후보를 추출

또는 비-thinking 모델인 `qwen2.5:14b-instruct`를 우선 시도하는 것이 현실적이다.
