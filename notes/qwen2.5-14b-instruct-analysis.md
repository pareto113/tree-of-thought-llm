# qwen2.5:14b-instruct ToT 적용 분석

> 실측 환경: qwen2.5:14b-instruct (Q4_K_M, 14.8B params, context 32768) on Ollama  
> 비교 대상: GPT-4o, qwen3.5:9b  
> 분석일: 2026-06-03

---

## 1. 모델 기본 특성

| 항목 | qwen2.5:14b-instruct |
|------|----------------------|
| 파라미터 | 14.8B |
| 양자화 | Q4_K_M (4-bit) |
| 컨텍스트 | 32,768 tokens |
| Thinking 모드 | **없음** (순수 instruction-following 모델) |
| 계열 | Qwen2 (Qwen3과 별개 계열) |

qwen3.5:9b와 달리 내부 추론(thinking) 단계가 없어, 프롬프트를 받으면 바로 응답 토큰을 생성한다.

---

## 2. 프롬프트별 실측 결과

### 2-1. Value 프롬프트 (sure / likely / impossible 판별)

**system prompt 없이 (원본 코드 그대로):**

| 입력 | 기대 | 실제 마지막 줄 | 파싱 가능 | 정답 |
|------|------|--------------|:---------:|:----:|
| 5 6 6 | sure | `**conclusion:** impossible` | ❌ | ❌ |
| 1 3 3 | impossible | `...the evaluation would also be **impossible**.` | ❌ | ❌ |
| 5 7 8 | likely | `final evaluation for **5, 7, 8**: **impossible**.` | ❌ | ❌ |
| 10 10 11 | impossible | `**conclusion:** impossible` | ❌ | ❌ |
| 3 4 8 | sure | `sure` | ✅ | ✅ |

**파싱 성공률 1/5 (20%)** — 마지막 줄에 마크다운 볼드, 문장형 설명이 붙어 파서가 값을 추출하지 못한다.

**system prompt 추가 후** (`"Always end your response with exactly one word: sure, likely, or impossible"`):

| 입력 | 기대 | 실제 마지막 줄 | 파싱 가능 | 정답 |
|------|------|--------------|:---------:|:----:|
| 5 6 6 | sure | `sure` | ✅ | ✅ |
| 1 3 3 | impossible | (마크다운 섞인 긴 문장) | ❌ | ❌ |
| 5 7 8 | likely | `likely` | ✅ | ✅ |
| 10 10 11 | impossible | `impossible` | ✅ | ✅ |
| 3 4 8 | sure | `sure` | ✅ | ✅ |

**파싱 성공률 4/5 (80%)** — system prompt 하나로 크게 개선되지만 완벽하지 않다.  
실패 케이스(`1 3 3`)에서 모델이 팩토리얼 등을 고려해 "likely"로 판단한 뒤 설명을 붙임 → 형식 지시를 무시했다.

---

### 2-2. Propose 프롬프트 (다음 스텝 제안)

**system prompt 없이:**

```
(실제 출력 예시)
For the input numbers `4, 5, 6, 10`, here are some possible operations:
- **4 + 5 = 9** (left: **9 6 10**)
- **5 - 4 = 1** (leaving us with `1, 6, 10`)
...Please specify if there's a particular rule...
```

`bfs.py`의 `split('\n')` 파서는 마크다운 불릿과 backtick이 섞인 이 형식을 처리할 수 없다. **파싱 완전 실패.**

**system prompt 추가 후** (`"Output ONLY lines in format: X op Y = Z (left: A B C)"`):

```
4 + 5 = 9 (left: 5 6 10)      ✗ (left 오류: 9 제외하고 나머지 6,10만 남겨야 하는데 5가 남음)
10 + 4 = 14 (left: 5 6 14)    ✓
4 * 5 = 20 (left: 5 6 10)     ✗ (left 오류: 20 추가 안 됨)
5 - 4 = 1 (left: 1 6 10)      ✓
10 - 4 = 6 (left: 5 5 6)      ✗ (left 오류: 5 두 번 등장)
10 / 4 = 2.5 (left: 2.5 5 6)  ✓ (단, 비정수 결과)
10 - 5 = 5 (left: 4 5 6)      ✓
```

**형식 준수: 8/8 (100%)** — 형식은 완벽히 따른다.  
**수학적 정확성: 4/7 (57%)** — `left:` 필드의 숫자 계산에서 오류 발생.

오류 패턴: 연산에 사용한 두 수를 제거하고 결과를 추가해야 하는데, 제거나 추가 중 하나를 빠뜨린다.

---

### 2-3. Vote 프롬프트 (Text Writing 태스크)

```
...The best choice is 2.
tokens: 251 | ms: 7,633
```

`"The best choice is {s}"` 패턴을 마지막 줄에 정확히 출력한다. **파싱 성공.**  
이 프롬프트는 형식이 유연(분석 내용 자유 + 마지막 줄만 고정)해서 별도 처리 없이도 동작한다.

---

### 2-4. value_last_step 프롬프트 (최종 답 검증)

```
입력: "Is (10 - 4) * (6 - 5) + 18 = 24 valid for 4 5 6 10?"
출력: "Judge:\nimpossible\n\nExplanation: 18 is not one of the input numbers..."
tokens: 69 | ms: 2,027
```

마지막에서 두 번째 줄이 `impossible`이고, 파서는 마지막 줄을 추출한다 → `Explanation: ...`이 마지막 줄이 되어 **파싱 실패**할 수 있다. 응답 구조에 따라 달라지므로 불안정하다.

---

## 3. 속도 비교

| 모델 / 모드 | Value 1회 | Propose 1회 | 특이사항 |
|-------------|:---------:|:-----------:|---------|
| GPT-4o | ~200ms | ~300ms | 원격 API |
| qwen3.5:9b thinking ON | **113,875ms** | **204,750ms** | thinking 토큰 폭발 |
| qwen3.5:9b thinking OFF | **26ms** | **20,649ms** | 형식 완전 이탈 |
| **qwen2.5:14b-instruct** | **6,000–12,000ms** | **8,000–20,000ms** | 형식 이탈 (수정 필요) |

qwen2.5:14b-instruct는 thinking 오버헤드가 없어 현실적인 속도를 가진다.  
Game24 ToT 100개 기준 추산:

```
64 calls/puzzle × 100 puzzles × 평균 10,000ms
= 약 17.8시간 (단일 스레드)
```

병렬 처리 없이는 느리지만, thinking ON 모드(213시간)와 달리 현실적인 범위에 있다.

---

## 4. 핵심 문제 요약

| 문제 | 심각도 | 원인 |
|------|:------:|------|
| Value 파싱 실패 (기본) | 🔴 치명 | 마지막 줄에 마크다운/문장 추가 |
| Propose 파싱 실패 (기본) | 🔴 치명 | 마크다운 불릿, 설명 문단 생성 |
| Propose left 수학 오류 (system prompt 후) | 🟡 중요 | 14B 모델의 수학 추론 한계 |
| value_last_step 불안정 | 🟡 중요 | 설명 줄이 마지막에 추가됨 |
| Vote 프롬프트 | 🟢 정상 | 유연한 형식이라 문제없음 |

---

## 5. qwen3.5:9b vs qwen2.5:14b-instruct 비교

| 항목 | qwen3.5:9b | qwen2.5:14b-instruct |
|------|-----------|---------------------|
| Thinking | 있음 (기본 ON) | **없음** |
| 속도 (think ON) | 치명적으로 느림 | 해당 없음 |
| 속도 (think OFF / 기본) | 26ms (빠름) | 6,000–12,000ms (보통) |
| 형식 준수 (기본) | ❌ 이탈 | ❌ 이탈 |
| 형식 준수 (system prompt) | ✅ 완벽 | ⚠️ 80% + 수학 오류 |
| 수학 정확성 | ✅ 높음 (think ON) | ⚠️ 보통 (left 오류 43%) |
| 파라미터 수 | 9.7B | 14.8B |
| 실용적 ToT 가능성 | ❌ (속도 or 형식 중 하나는 포기) | ⚠️ 수정 시 부분 가능 |

---

## 6. 결론 및 적용 전략

### 코드 수정 없이는 동작하지 않는다

두 모델 모두 system prompt 없이는 format이 깨져 파서가 실패한다. 최소한 `models.py`에서 모든 API 호출 시 형식 강제 system prompt를 주입해야 한다.

### system prompt 추가 후 예상 동작

```
Value 프롬프트: 파싱 성공률 ~80% (20%는 여전히 실패)
Propose 프롬프트: 형식은 통과, 수학적 오류 ~43%
Vote 프롬프트:   수정 없이도 정상
value_last_step: 불안정, 별도 처리 필요
```

### 추가로 필요한 파서 수정

`bfs.py`의 `get_proposals()`에서 `left:` 필드 수학 검증 로직이 없기 때문에, 잘못된 `left` 값을 가진 후보가 BFS 트리에 올라가 이후 단계의 평가를 오염시킨다.

```python
# 현재 코드 (검증 없음)
proposals = gpt(propose_prompt, n=1, stop=None)[0].split('\n')
return [y + _ + '\n' for _ in proposals]

# 필요한 추가: left 값 재계산 또는 검증 후 필터링
```

### 현실적 권고

| 목적 | 권장 모델 | 필요 수정 |
|------|-----------|-----------|
| 빠른 기능 검증 (정확도 무관) | qwen2.5:14b-instruct | system prompt 주입 |
| 논문 수준 재현 | GPT-4o | 없음 |
| 로컬 + 최고 품질 | qwen3.6:27b | system prompt + 속도 감수 |

qwen2.5:14b-instruct는 "동작은 하지만 정확도가 낮은" 수준으로 사용 가능하다. 파이프라인 디버깅이나 프롬프트 설계 검증 용도로는 적합하지만, GPT-4 수준의 결과를 기대하기는 어렵다.
