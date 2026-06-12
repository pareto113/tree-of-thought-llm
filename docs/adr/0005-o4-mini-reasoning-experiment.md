# o4-mini IO×1 추가 실험 (논문 외 확장 실험)

논문 발표(2023) 이후 OpenAI가 내부 추론(internal reasoning)을 수행하는 o-series 모델을
출시했다. 외부 구조(ToT)가 필요하지 않을 수도 있다는 가설을 검증하기 위해 추가 실험을 진행한다.

## 선택한 모델: o4-mini

o1(원래 목표 모델)은 deprecated 직전 상태이고 비용이 prohibitive하다.
o4-mini를 대신 선택한다.

| 모델 | reasoning tokens/콜 | n>1 | IO×1 예상 비용 |
|------|-------------------|-----|-------------|
| o1 | ~2,000 | ❌ | ~$12 |
| o3-mini | 2,000+ (부족) | ✅ | 부적합 |
| **o4-mini** | **~832** | **✅** | **~$0.40** |

## 실험 범위: IO×1만

o4-mini는 IO 프롬프트만으로도 내부 CoT를 수행한다.
외부 CoT 프롬프트 추가 효과가 미미할 것으로 예상되어 IO×1 단일 비교로 충분하다.

## 핵심 연구 질문

> "외부 구조(ToT with GPT-4o mini) 없이 내부 추론 모델(o4-mini)의 IO 단일 샘플만으로
> GPT-4o mini ToT b=5와 경쟁할 수 있는가?"

## Considered Options

- **o1 IO×1**: 원래 목표. reasoning 최초 모델로 상징성 있으나 비용($12) 및
  n>1 미지원으로 탈락.
- **o3-mini IO×1**: n>1 지원하나 2,000 토큰으로도 답변 미완성. 탈락.
- **o4-mini IO×1** ← 채택: 최소 비용, 최고 효율, n>1 지원.

## Consequences

- 실험 결과는 "reasoning 모델 시대에 ToT가 여전히 유효한가"라는 보고서 논점에 기여한다.
- o4-mini는 시스템 프롬프트 및 temperature 처리가 GPT-4o mini와 다를 수 있어
  models.py에 별도 분기 처리가 필요하다.
- n>1 미사용으로 best-of-k 비교는 불가하며 단일 샘플 결과의 분산이 크다.
