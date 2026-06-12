# ADR-0006: ToT propose_prompt를 3-shot으로 변경 (gpt-4o-mini 대응)

## 상태

채택

## 배경

논문 원본(Yao et al., 2023)의 ToT propose_prompt는 1-shot (4수→3수 예시 하나)이다.
이 설정에서 GPT-4는 74% 성공률을 기록했다.

그러나 gpt-4o-mini로 실험 시 propose step에서 `left:` 숫자 추적 오류가 첫 단계부터
발생하여 BFS 전체가 무효화되었고, 100개 중 0%를 기록했다.

논문 Appendix B.2는 GPT-3.5에서도 동일한 현상이 발생해 **1-shot → 3-shot으로
변경해야 실험이 가능했다고 명시**한다:

> "we changed 1-shot proposal prompt to 3-shot to make it work"

## 결정

propose_prompt를 3-shot으로 변경한다.

- 기존 4수→3수 예시 유지
- 3수→2수 예시 추가 (`Input: 4 6 8`)
- 2수→1수 예시 추가 (`Input: 3 8`)

변경 후 10-puzzle 테스트: **0% → 70%**

## 근거

gpt-4o-mini는 GPT-4 대비 출력 토큰 기준 25배 저렴한($0.60 vs $15) 경량 모델이다.
본 실험은 재현이 아닌 적용 실험(ADR-0001)이므로, 논문이 GPT-3.5에 적용한 것과
동일한 논리로 경량 모델에 필요한 최소한의 조정을 허용한다.

## 감수해야 할 사항

- **비교 조건 편차**: 논문의 GPT-4 결과는 1-shot 기반. 결과 해석 시 이 차이를 명시해야 함.
- **입력 토큰 증가**: 3-shot은 1-shot 대비 propose prompt 길이가 약 2배. 비용 소폭 증가.

## Considered Options

- **1-shot 유지**: 논문과 동일 조건이나 gpt-4o-mini에서 0% → 실험 불가
- **3-shot 채택** ← 채택: GPT-3.5 precedent 있음, 적용 실험 목적에 부합
