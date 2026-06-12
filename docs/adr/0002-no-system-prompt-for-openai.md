# OpenAI 실험에서 시스템 프롬프트 주입 제거

현재 `models.py`의 `_SYSTEM_PROMPT`는 Qwen 14b가 마크다운을 추가하는 문제를 막기 위해 삽입된 것이다. GPT-4o mini 실험에서는 이를 제거한다. 원 논문 프롬프트는 시스템 프롬프트 없이 설계되었고, GPT-4o mini는 few-shot 형식을 별도 지시 없이도 충분히 따른다.

## Considered Options

- **제거** ← 채택: 논문과 동일한 조건, few-shot 예시와 충돌 없음.
- **유지**: 포맷 오류 방지 효과가 있으나 논문과 조건이 달라져 비교 공정성 훼손.

## Consequences

Qwen 14b(Ollama) 실험과 GPT-4o mini(OpenAI) 실험은 시스템 프롬프트 유무가 다르다. 보고서에서 두 모델을 비교할 때 이 차이를 주석으로 명시해야 한다.
