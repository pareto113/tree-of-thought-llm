#!/usr/bin/env python3
"""
CoT Correct 불일치 진단 스크립트.

Figure 3(b) step 분석의 Correct(7%)와 Table 2 성공률(4%)이 다른 이유를 확인한다.

- step 분석 correct: _cot_failure_step()이 None 반환 = 중간 경로에서 left:24 도달
- Table 2 correct: accs=1 = 최종 Answer 수식이 수학적으로 검증됨

Usage: python scripts/diagnose_cot_correct.py
"""

import json
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from evaluate_log import _cot_failure_step

LOG_PATH = "logs/game24/gpt-4o-mini_0.7_naive_cot_sample_1_start900_end1000.json"


def main():
    with open(LOG_PATH) as f:
        data = json.load(f)

    step_correct   = 0
    table_correct  = 0
    fmt_error_idxs = []

    for entry in data:
        ys   = entry.get('ys', [])
        accs = ([info['r'] for info in entry['infos']]
                if 'infos' in entry else entry.get('accs', [0]))

        step_ok  = any(_cot_failure_step(y) is None for y in ys)
        table_ok = any(accs)

        if step_ok:
            step_correct += 1
        if table_ok:
            table_correct += 1
        if step_ok and not table_ok:
            fmt_error_idxs.append(entry['idx'])

    fmt_error = len(fmt_error_idxs)

    print("── CoT Correct 불일치 진단 ────────────────────────────────")
    print(f"step 분석 correct (left:24 경로 도달):  {step_correct}/100 = {step_correct}%")
    print(f"Table 2 correct  (Answer 수식 검증):   {table_correct}/100 = {table_correct}%")
    print(f"CoT answer_fmt_error                   {fmt_error}/100 = {fmt_error}%")
    print()
    print("결론: step 분석은 중간 경로(left:24 도달)를 기준으로 하고,")
    print("      Table 2는 최종 Answer 수식의 수학적 정확도를 기준으로 한다.")
    print("      차이(3%)가 CoT의 answer_fmt_error에 해당한다.")
    print()
    print(f"Figure 3(b) CoT 올바른 수치:")
    print(f"  Ans. fmt error: {fmt_error}%")
    print(f"  Correct:        {table_correct}%")
    print()
    if fmt_error_idxs:
        print(f"answer_fmt_error 발생 puzzle idx: {fmt_error_idxs}")


if __name__ == '__main__':
    main()
