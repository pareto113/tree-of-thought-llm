# Tree of Thoughts — 실험 재현 프로젝트

Yao et al. (2023) "Tree of Thoughts" 논문의 방법론을 GPT-4o mini에 적용하고, 논문 원본(GPT-4) 결과와 비교 분석하는 보고서 작성 프로젝트.

## Language

### 실험 유형

**적용 실험 (Application Experiment)**:
GPT-4o mini로 ToT/CoT/IO를 동일 조건 하에 실행하고 논문(GPT-4) 수치와 비교하는 실험. "재현"이 아님 — 모델이 다르므로 결과 일치를 목표로 하지 않는다.
_Avoid_: 재현 실험, reproduction

**베이스라인 (Baseline)**:
트리 탐색 없이 단일 프롬프트로 답을 생성하는 비교 기준 방법. IO(standard)와 CoT 두 종류가 있다.
_Avoid_: 기본 방법, 기준선

**실험 조건 (Run Configuration)**:
한 번의 실험을 정의하는 파라미터 조합. 모델, 방법(IO/CoT/ToT), 퍼즐 범위, 샘플 수를 포함한다.

### 방법론

**Thought**:
ToT에서 LLM이 생성하는 중간 추론 단계 하나. Game24에서는 "남은 숫자로 수행하는 단일 산술 연산"이 한 Thought다.

**IO (Input-Output)**:
프롬프트에 입력만 주고 바로 최종 답을 요청하는 방식. 코드상 `naive_solve` + `standard` 프롬프트.
_Avoid_: standard, direct

**CoT (Chain-of-Thought)**:
단계별 추론 과정을 포함한 프롬프트로 답을 요청하는 방식. 코드상 `naive_solve` + `cot` 프롬프트.

**ToT (Tree of Thoughts)**:
Thought를 트리 구조로 탐색하며 BFS/DFS로 최적 경로를 찾는 방식. Game24에서는 `propose + value + greedy` 조합.

### 평가 지표

**cnt_any**:
전체 퍼즐 중 샘플 n개 중 1개라도 정답을 낸 퍼즐의 비율. 논문의 주 지표.
_Avoid_: 성공률 (모호함)

**cnt_avg**:
전체 샘플에 걸친 평균 정답률. cnt_any보다 엄격한 지표.
_Avoid_: 평균 정확도
