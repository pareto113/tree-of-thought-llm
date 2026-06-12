# 형식 강제용 시스템 프롬프트 적용 (GPT-4o mini)

smoke test 결과, 시스템 프롬프트 없이는 GPT-4o mini가 propose 단계에서 번호 목록·마크다운
볼드체·설명 텍스트를 추가해 파서 regex가 0% 매칭한다. value 단계도 마지막 줄에 단일 키워드
대신 긴 문장을 출력해 `value_outputs_unwrap`이 실패한다. 시스템 프롬프트는 Qwen용 언어
지시와 달리 **형식 준수**만을 목적으로 한다.

## Considered Options

- **형식 강제 시스템 프롬프트 적용** ← 채택: propose 형식 0% → 100%, value 파싱 정상화.
- **프롬프트 없이 진행**: ToT 실험 자체가 불가. propose/value 파싱 전면 실패.
- **프롬프트 엔지니어링으로 user 메시지에 형식 지시 삽입**: 각 프롬프트 파일 수정 필요,
  논문 원본 프롬프트와의 차이가 더 커짐.

## Consequences

- GPT-4 원본 실험(시스템 프롬프트 없음)과 조건이 다르다. 보고서에서 이 차이를 명시한다.
- 시스템 프롬프트 내용:
  `"You are a concise assistant. Follow the output format shown in the examples exactly.
  Do not add explanations, numbered lists, markdown, or any text beyond what the format requires."`
