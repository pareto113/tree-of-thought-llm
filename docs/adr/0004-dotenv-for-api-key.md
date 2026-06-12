# python-dotenv로 API 키 관리

장시간 실험(100 퍼즐 × 3가지 방법)을 반복 실행하므로, 터미널 세션이 끊기거나
resume 시 새 쉘에서 실행하는 경우에도 OPENAI_API_KEY가 안정적으로 로드되어야 한다.

## Considered Options

- **python-dotenv 자동 로드** ← 채택: run.py 실행 시 항상 .env를 읽음. 세션 상태에 무관.
- **수동 export**: 단발성 실행엔 충분하지만, 터미널 재시작·resume 시마다 재입력 필요.
- **~/.bashrc 전역 등록**: 키가 모든 프로세스에 노출되어 범위가 지나치게 넓음.

## Consequences

- `.env` 파일은 `.gitignore`에 이미 등록되어 있어 커밋되지 않는다.
- `.env.example`을 저장소에 포함해 키 형식을 문서화한다.
- `python-dotenv`를 `requirements.txt`에 추가한다.
