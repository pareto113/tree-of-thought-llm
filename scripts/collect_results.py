#!/usr/bin/env python3
"""
보고서용 수치 일괄 집계 스크립트
Usage: python scripts/collect_results.py

출력 섹션:
  4.1  방법별 성공률          (논문 Table 2 대응)
  4.2  탐색 비용 대비 성공률   (논문 Figure 3(a) 대응)
  4.3  추론 단계별 오류 분포   (논문 Figure 3(b) 대응)
  4.4  방법별 API 비용        (논문 Table 7 대응)
"""

import json
import os
import sys
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from evaluate_log import compute_nodes_visited, analyze_step_failures, _is_io_standard

LOG_DIR = "logs/game24"

LOGS = [
    ("IO×1",          "gpt-4o-mini_0.7_naive_standard_sample_1_start900_end1000.json"),
    ("IO×100",        "gpt-4o-mini_0.7_naive_standard_sample_100_start900_end1000.json"),
    ("CoT×1",         "gpt-4o-mini_0.7_naive_cot_sample_1_start900_end1000.json"),
    ("CoT×100",       "gpt-4o-mini_0.7_naive_cot_sample_100_start900_end1000.json"),
    ("ToT b=1",       "gpt-4o-mini_0.7_propose1_value3_greedy1_start900_end1000.json"),
    ("ToT b=2",       "gpt-4o-mini_0.7_propose1_value3_greedy2_start900_end1000.json"),
    ("ToT b=3",       "gpt-4o-mini_0.7_propose1_value3_greedy3_start900_end1000.json"),
    ("ToT b=4",       "gpt-4o-mini_0.7_propose1_value3_greedy4_start900_end1000.json"),
    ("ToT b=5",       "gpt-4o-mini_0.7_propose1_value3_greedy5_start900_end1000.json"),
    ("o4-mini IO×1",  "o4-mini_1.0_naive_standard_sample_1_start900_end1000.json"),
]

# Figure 3(b): 이 두 실험만 step 실패 분포 집계
STEP_FAIL_LABELS = {"CoT×1", "ToT b=5"}


def load_log(fname):
    with open(os.path.join(LOG_DIR, fname)) as f:
        return json.load(f)


def compute_accuracy(data):
    """cnt_any, cnt_sc(CoT 계열에만 적용), 비용을 계산한다."""
    is_io_std = _is_io_standard(data)
    is_tot    = any('steps' in e and e['steps'] for e in data)
    # CoT-SC는 CoT naive_run에만 의미 있음 (IO standard, ToT 제외)
    sc_applicable = not is_io_std and not is_tot

    cnt_any = cnt_sc = 0

    for entry in data:
        ys   = entry.get('ys', [])
        accs = ([info['r'] for info in entry['infos']]
                if 'infos' in entry else entry.get('accs', [0]))
        cnt_any += int(any(accs))
        if sc_applicable and ys:
            answers = [y.strip().split('\n')[-1] for y in ys]
            top     = Counter(answers).most_common(1)[0][0]
            idx     = answers.index(top)
            cnt_sc += int(accs[idx]) if idx < len(accs) else 0

    n     = len(data)
    usage = data[-1].get('usage_so_far', {})
    return {
        'n':        n,
        'cnt_any':  cnt_any,
        'rate_any': cnt_any / n if n else 0,
        'cnt_sc':   cnt_sc if sc_applicable else None,
        'rate_sc':  cnt_sc / n if sc_applicable else None,
        'cost':     usage.get('cost'),
    }


def main():
    results = {}
    for label, fname in LOGS:
        path = os.path.join(LOG_DIR, fname)
        if not os.path.exists(path):
            print(f"[경고] 로그 없음: {path}", file=sys.stderr)
            continue
        data      = load_log(fname)
        acc       = compute_accuracy(data)
        nodes     = compute_nodes_visited(data)
        step_fail = analyze_step_failures(data) if label in STEP_FAIL_LABELS else None
        results[label] = {'acc': acc, 'nodes': nodes, 'step_fail': step_fail}

    W = 68
    sep = '─' * W

    # ── 4.1 방법별 성공률 ─────────────────────────────────────────
    print(f"\n{'═'*W}")
    print(f"  4.1  방법별 성공률  (논문 Table 2 대응)")
    print(f"{'═'*W}")
    print(f"  {'방법':<16}  {'성공률(any)':>10}  {'CoT-SC':>8}  {'n':>5}")
    print(f"  {sep}")
    for label, _ in LOGS:
        if label not in results:
            continue
        r    = results[label]
        rate = f"{r['acc']['rate_any']*100:.0f}%"
        sc   = (f"{r['acc']['rate_sc']*100:.0f}%"
                if r['acc']['rate_sc'] is not None else "—")
        print(f"  {label:<16}  {rate:>10}  {sc:>8}  {r['acc']['n']:>5}")

    # ── 4.2 탐색 비용 대비 성공률 ─────────────────────────────────
    print(f"\n{'═'*W}")
    print(f"  4.2  탐색 비용 대비 성공률  (논문 Figure 3(a) 대응)")
    print(f"  * nodes_visited: naive_run은 n_generate_sample, ToT는 evaluate된 후보 수")
    print(f"{'═'*W}")
    print(f"  {'방법':<16}  {'nodes/puzzle':>12}  {'성공률':>6}")
    print(f"  {sep}")
    for label, _ in LOGS:
        if label not in results:
            continue
        r     = results[label]
        nodes = r['nodes']['per_puzzle']
        rate  = f"{r['acc']['rate_any']*100:.0f}%"
        print(f"  {label:<16}  {nodes:>12.1f}  {rate:>6}")

    # ── 4.3 추론 단계별 오류 분포 ─────────────────────────────────
    print(f"\n{'═'*W}")
    print(f"  4.3  추론 단계별 오류 분포  (논문 Figure 3(b) 대응)")
    print(f"  대상: CoT×1 vs ToT b=5")
    print(f"{'═'*W}")
    for label in ("CoT×1", "ToT b=5"):
        if label not in results or results[label]['step_fail'] is None:
            continue
        sf = results[label]['step_fail']
        print(f"\n  [{label}]")
        if 'n/a' in sf:
            print(f"    {sf['n/a']}")
            continue
        for k, rate in sf['rates'].items():
            if k == 'correct':
                lbl = 'Correct'
            elif k == 'answer_fmt_error':
                lbl = 'Ans fmt err'
            else:
                lbl = f'Step {k} 실패'
            cnt   = sf['distribution'][k]
            total = sf['total']
            print(f"    {lbl:<16}: {rate*100:.1f}%  ({cnt}/{total})")

    # ── 4.4 방법별 API 비용 ───────────────────────────────────────
    print(f"\n{'═'*W}")
    print(f"  4.4  방법별 API 비용  (논문 Table 7 대응)")
    print(f"  * resume 분할 실행된 실험은 마지막 세션 비용만 집계됨 (과소 추정 가능)")
    print(f"{'═'*W}")
    print(f"  {'방법':<16}  {'비용':>10}")
    print(f"  {sep}")
    for label, _ in LOGS:
        if label not in results:
            continue
        cost = results[label]['acc']['cost']
        cost_str = f"${cost:.4f}" if cost is not None else "—"
        print(f"  {label:<16}  {cost_str:>10}")

    print()


if __name__ == '__main__':
    main()
