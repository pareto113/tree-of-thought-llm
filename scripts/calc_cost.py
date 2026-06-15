#!/usr/bin/env python3
"""
실험별 실제 API 비용 계산 스크립트.

usage_so_far는 세션 내 누적값이므로, 연속 엔트리 간 차분으로 퍼즐별 토큰을 역산한다.
세션 재시작 지점(usage_so_far가 감소하는 지점)을 감지해 모든 세션에 걸쳐 합산한다.

가격표:
  gpt-4o-mini: input $0.15 / 1M tokens, output $0.60 / 1M tokens
  o4-mini:     input $1.10 / 1M tokens, output $4.40 / 1M tokens

Usage: python scripts/calc_cost.py
"""

import json
import os

LOG_DIR = "logs/game24"

# (label, filename, price_input_per_token, price_output_per_token)
LOGS = [
    ("IO×1",         "gpt-4o-mini_0.7_naive_standard_sample_1_start900_end1000.json",   0.15/1e6, 0.60/1e6),
    ("IO×100",       "gpt-4o-mini_0.7_naive_standard_sample_100_start900_end1000.json", 0.15/1e6, 0.60/1e6),
    ("CoT×1",        "gpt-4o-mini_0.7_naive_cot_sample_1_start900_end1000.json",        0.15/1e6, 0.60/1e6),
    ("CoT×100",      "gpt-4o-mini_0.7_naive_cot_sample_100_start900_end1000.json",      0.15/1e6, 0.60/1e6),
    ("ToT b=1",      "gpt-4o-mini_0.7_propose1_value3_greedy1_start900_end1000.json",   0.15/1e6, 0.60/1e6),
    ("ToT b=2",      "gpt-4o-mini_0.7_propose1_value3_greedy2_start900_end1000.json",   0.15/1e6, 0.60/1e6),
    ("ToT b=3",      "gpt-4o-mini_0.7_propose1_value3_greedy3_start900_end1000.json",   0.15/1e6, 0.60/1e6),
    ("ToT b=4",      "gpt-4o-mini_0.7_propose1_value3_greedy4_start900_end1000.json",   0.15/1e6, 0.60/1e6),
    ("ToT b=5",      "gpt-4o-mini_0.7_propose1_value3_greedy5_start900_end1000.json",   0.15/1e6, 0.60/1e6),
    ("o4-mini IO×1", "o4-mini_1.0_naive_standard_sample_1_start900_end1000.json",       1.10/1e6, 4.40/1e6),
]


def calc_tokens(data: list):
    """모든 세션에 걸쳐 prompt/completion 토큰 합산.

    usage_so_far가 감소하는 지점을 세션 재시작으로 감지한다.
    Returns (prompt_tokens, completion_tokens, n_sessions).
    """
    total_prompt = 0
    total_completion = 0
    n_sessions = 1

    prev_prompt = 0
    prev_completion = 0

    for entry in data:
        u = entry.get('usage_so_far', {})
        if not u:
            continue

        cur_prompt     = u.get('prompt_tokens', 0)
        cur_completion = u.get('completion_tokens', 0)

        if cur_prompt < prev_prompt or cur_completion < prev_completion:
            # 세션 재시작: 이전 세션 마지막 누적값은 이미 더해진 상태
            # 새 세션의 현재 엔트리 값 그대로 더함
            total_prompt     += cur_prompt
            total_completion += cur_completion
            n_sessions += 1
        else:
            # 같은 세션: 증분만 더함
            total_prompt     += cur_prompt - prev_prompt
            total_completion += cur_completion - prev_completion

        prev_prompt     = cur_prompt
        prev_completion = cur_completion

    return total_prompt, total_completion, n_sessions


def main():
    W = 70
    print(f"\n{'═'*W}")
    print(f"  API 비용 계산 (gpt-4o-mini: $0.15/$0.60 per 1M, o4-mini: $1.10/$4.40 per 1M)")
    print(f"{'═'*W}")
    print(f"  {'실험':<16}  {'prompt (M)':>10}  {'compl. (M)':>10}  {'비용':>9}  {'세션':>4}")
    print(f"  {'─'*W}")

    total_cost = 0.0
    for label, fname, price_in, price_out in LOGS:
        path = os.path.join(LOG_DIR, fname)
        if not os.path.exists(path):
            print(f"  {label:<16}  (로그 없음)")
            continue

        with open(path) as f:
            data = json.load(f)

        prompt_tok, completion_tok, n_sess = calc_tokens(data)
        cost = prompt_tok * price_in + completion_tok * price_out
        total_cost += cost

        print(f"  {label:<16}  {prompt_tok/1e6:>10.4f}  {completion_tok/1e6:>10.4f}"
              f"  ${cost:>8.4f}  {n_sess:>4}")

    print(f"  {'─'*W}")
    print(f"  {'합계':<16}  {'':>10}  {'':>10}  ${total_cost:>8.4f}")
    print()


if __name__ == '__main__':
    main()
