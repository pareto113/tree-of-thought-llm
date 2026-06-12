# Ollama 백엔드 제거, OpenAI 전용으로 교체

Qwen 14b (Ollama) 실험은 완료되어 로그가 존재하므로, 이후 실험은 GPT-4o mini (OpenAI API)만 사용한다. models.py를 OpenAI SDK 전용으로 교체하고 Ollama 관련 코드를 삭제한다.

## Considered Options

- **OpenAI 전용 교체** ← 채택: 단순하고 코드가 명확해짐. Ollama 로그는 이미 존재.
- **두 백엔드 동시 지원**: 유지보수 복잡도 증가, 현재 필요 없음.

## Consequences

Ollama를 다시 쓰려면 git history에서 복원해야 한다.
