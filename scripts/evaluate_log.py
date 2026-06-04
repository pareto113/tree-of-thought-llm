"""
ToT 실험 로그 평가 스크립트
Usage: python scripts/evaluate_log.py <log_file.json> [--save]

1) 형식(format) 평가: propose/value 출력이 파서 기대 형식을 준수하는지
2) 정확도(accuracy) 평가: 최종 답이 수학적으로 올바른지

--save 옵션: 결과를 logs/eval/<원본파일명>_eval.json 으로 저장
"""

import json
import re
import sys
import os
import argparse
from collections import defaultdict


# ── 형식 검사 헬퍼 ────────────────────────────────────────────────

PROPOSE_RE = re.compile(
    r'^([\d.]+(?:\.\.\.)?)\s*([+\-*/])\s*([\d.]+(?:\.\.\.)?)\s*=\s*([\d.]+(?:\.\.\.)?)\s*\(left:\s*([\d. .]+?)\)\s*$'
)

def _parse_float(s: str) -> float:
    """'1.666...' 같은 GPT-4 반복소수 표기도 처리."""
    return float(s.replace('...', ''))

def parse_proposal(line: str):
    """propose 한 줄 파싱. 성공 시 (a, op, b, result, left_nums) 반환."""
    m = PROPOSE_RE.match(line.strip())
    if not m:
        return None
    a, op, b, result, left_str = m.groups()
    # left_str에서 '1.666...' 같은 토큰도 처리
    left_tokens = re.findall(r'[\d.]+(?:\.\.\.)?', left_str)
    return _parse_float(a), op, _parse_float(b), _parse_float(result), [_parse_float(x) for x in left_tokens]

def check_proposal_math(a, op, b, result, left_nums, input_nums):
    """수식과 left 필드가 수학적으로 맞는지 검증."""
    ops = {'+': a+b, '-': a-b, '*': a*b, '/': a/b if b != 0 else None}
    calc = ops.get(op)
    if calc is None or abs(calc - result) > 0.01:
        return False, "수식 오류"

    remaining = sorted(input_nums)
    try:
        remaining.remove(round(a, 4))
        remaining.remove(round(b, 4))
    except ValueError:
        return False, "입력 숫자 불일치"
    expected_left = sorted(remaining + [round(result, 4)])
    actual_left   = sorted(round(x, 4) for x in left_nums)
    if expected_left != actual_left:
        return False, f"left 오류 (기대:{expected_left} 실제:{actual_left})"
    return True, "OK"

def get_input_nums(line: str):
    """'left: a b c' 또는 입력 문자열에서 숫자 추출."""
    return [float(x) for x in re.findall(r'[\d.]+', line)]


# ── 메인 평가 함수 ────────────────────────────────────────────────

def evaluate(log_path: str, save: bool = False):
    with open(log_path) as f:
        data = json.load(f)

    n_puzzles = len(data)

    # ── 1. 형식 평가 ──────────────────────────────────────────────
    fmt = {
        'propose_total':     0,   # 전체 propose 줄 수
        'propose_empty':     0,   # 빈 줄
        'propose_fmt_ok':    0,   # 형식 일치
        'propose_math_ok':   0,   # 수학 정확
        'propose_math_err':  defaultdict(int),  # 오류 유형별
        'value_total':       0,   # value 평가 횟수
        'value_parseable':   0,   # sure/likely/impossible 파싱 성공
        'value_dist':        defaultdict(int),  # 분포
    }

    for entry in data:
        steps = entry.get('steps', [])
        for step_i, step in enumerate(steps):
            x = step['x']
            ys_before = step['ys']   # 이 step 이전 상태들
            new_ys    = step['new_ys']
            values    = step['values']

            # ── propose 형식 검사
            for y in new_ys:
                # y = 이전 상태 + 새 줄. 마지막 줄이 이번 propose 결과
                lines = y.strip().split('\n')
                new_line = lines[-1] if lines else ''
                fmt['propose_total'] += 1

                if not new_line.strip():
                    fmt['propose_empty'] += 1
                    continue

                parsed = parse_proposal(new_line)
                if parsed is None:
                    continue
                fmt['propose_fmt_ok'] += 1

                # left 이전 상태의 숫자 파악
                if step_i == 0:
                    input_nums = get_input_nums(x)
                else:
                    prev_line = lines[-2] if len(lines) >= 2 else ''
                    left_match = re.search(r'left:\s*([\d. ]+)\)', prev_line)
                    if left_match:
                        input_nums = [float(v) for v in left_match.group(1).split()]
                    else:
                        input_nums = get_input_nums(x)

                a, op, b, result, left_nums = parsed
                ok, reason = check_proposal_math(a, op, b, result, left_nums, input_nums)
                if ok:
                    fmt['propose_math_ok'] += 1
                else:
                    fmt['propose_math_err'][reason] += 1

            # ── value 형식 검사
            for v_score in values:
                # values는 숫자 점수이므로, 원본 출력 텍스트는 로그에 없음
                # 0.001=impossible, 0=파싱실패, >0=sure/likely
                fmt['value_total'] += 1
                if v_score == 0:
                    fmt['value_dist']['파싱실패(0점)'] += 1
                elif abs(v_score - 0.001) < 0.0001:
                    fmt['value_parseable'] += 1
                    fmt['value_dist']['impossible'] += 1
                elif v_score % 1 == 0 and v_score > 0:
                    fmt['value_parseable'] += 1
                    if v_score >= 20:
                        fmt['value_dist']['sure'] += 1
                    else:
                        fmt['value_dist']['likely'] += 1
                else:
                    fmt['value_parseable'] += 1
                    fmt['value_dist']['mixed'] += 1

    # ── 2. 정확도 평가 ────────────────────────────────────────────
    cnt_avg = 0
    cnt_any = 0
    results = []

    for entry in data:
        idx   = entry['idx']
        ys    = entry['ys']
        # naive_standard는 'accs', 나머지는 'infos' 사용
        if 'infos' in entry:
            accs = [info['r'] for info in entry['infos']]
        else:
            accs = entry.get('accs', [0])
        cnt_avg += sum(accs) / len(accs)
        cnt_any += int(any(accs))
        results.append({
            'idx':     idx,
            'input':   entry['steps'][0]['x'] if entry.get('steps') else '?',
            'any':     any(accs),
            'avg':     sum(accs) / len(accs),
            'answers': [y.strip().split('\n')[-1] for y in ys],
        })

    # ── 출력 ──────────────────────────────────────────────────────
    sep = '─' * 60

    print(f"\n{'═'*60}")
    print(f"  로그: {log_path}")
    print(f"  퍼즐 수: {n_puzzles}")
    print(f"{'═'*60}")

    print(f"\n【 1. 형식(Format) 평가 】")
    print(sep)

    p_total = fmt['propose_total']
    p_fmt   = fmt['propose_fmt_ok']
    p_math  = fmt['propose_math_ok']
    p_empty = fmt['propose_empty']
    print(f"  Propose 출력")
    if p_total == 0:
        print(f"    (naive_run — propose 단계 없음)")
    else:
        print(f"    전체 줄:       {p_total:>5}")
        print(f"    빈 줄:         {p_empty:>5}  ({p_empty/p_total*100:.1f}%)")
        print(f"    형식 일치:     {p_fmt:>5}  ({p_fmt/p_total*100:.1f}%)")
        if p_fmt > 0:
            print(f"    수학 정확:     {p_math:>5}  ({p_math/p_fmt*100:.1f}% of 형식 일치)")
            if fmt['propose_math_err']:
                print(f"    수학 오류 유형:")
                for reason, cnt in fmt['propose_math_err'].items():
                    print(f"      {reason}: {cnt}회")

    print()
    v_total = fmt['value_total']
    v_parse = fmt['value_parseable']
    print(f"  Value 평가")
    if v_total == 0:
        print(f"    (naive_run — value 평가 단계 없음)")
    else:
        print(f"    전체 호출:     {v_total:>5}")
        print(f"    파싱 성공:     {v_parse:>5}  ({v_parse/v_total*100:.1f}%)")
        print(f"    분포:")
        for k, v in sorted(fmt['value_dist'].items()):
            print(f"      {k:<12}: {v:>4}회  ({v/v_total*100:.1f}%)")

    print(f"\n【 2. 정확도(Accuracy) 평가 】")
    print(sep)
    print(f"  {'idx':<6} {'입력':<16} {'성공':<6} {'avg_r':<8}  최선 답")
    print(f"  {'-'*58}")
    for r in results:
        mark = '✅' if r['any'] else '❌'
        ans  = r['answers'][0] if r['answers'] else '-'
        print(f"  {r['idx']:<6} {r['input']:<16} {mark:<6} {r['avg']:<8.3f}  {ans}")

    print(f"\n  cnt_avg (평균 정답률): {cnt_avg/n_puzzles:.3f}")
    print(f"  cnt_any (1개 이상 정답): {cnt_any}/{n_puzzles} = {cnt_any/n_puzzles*100:.0f}%")

    usage = data[-1].get('usage_so_far', {})
    if usage:
        print(f"\n  누적 토큰: prompt={usage.get('prompt_tokens',0):,} / "
              f"completion={usage.get('completion_tokens',0):,} / "
              f"cost=${usage.get('cost',0):.4f}")
    print()

    # ── JSON 저장 ─────────────────────────────────────────────────
    eval_data = {
        'source_log': log_path,
        'n_puzzles':  n_puzzles,
        'format': {
            'propose': {
                'total':        fmt['propose_total'],
                'empty':        fmt['propose_empty'],
                'fmt_ok':       fmt['propose_fmt_ok'],
                'fmt_ok_rate':  round(fmt['propose_fmt_ok'] / max(fmt['propose_total'], 1), 4) if fmt['propose_total'] else None,
                'math_ok':      fmt['propose_math_ok'],
                'math_ok_rate': round(fmt['propose_math_ok'] / max(fmt['propose_fmt_ok'], 1), 4) if fmt['propose_fmt_ok'] else None,
                'math_errors':  dict(fmt['propose_math_err']),
            },
            'value': {
                'total':          fmt['value_total'],
                'parseable':      fmt['value_parseable'],
                'parseable_rate': round(fmt['value_parseable'] / max(fmt['value_total'], 1), 4) if fmt['value_total'] else None,
                'distribution':   dict(fmt['value_dist']),
            },
        },
        'accuracy': {
            'cnt_avg':  round(cnt_avg / n_puzzles, 4),
            'cnt_any':  cnt_any,
            'cnt_any_rate': round(cnt_any / n_puzzles, 4),
            'per_puzzle': results,
        },
        'usage': usage,
    }

    if save:
        log_dir  = os.path.dirname(os.path.abspath(log_path))
        log_stem = os.path.splitext(os.path.basename(log_path))[0]
        eval_dir = os.path.join(os.path.dirname(log_dir), 'eval')
        os.makedirs(eval_dir, exist_ok=True)
        out_path = os.path.join(eval_dir, f'{log_stem}_eval.json')
        with open(out_path, 'w') as f:
            json.dump(eval_data, f, indent=2, ensure_ascii=False)
        print(f"  저장 완료: {out_path}\n")

    return eval_data


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='ToT 실험 로그 평가')
    parser.add_argument('log', help='평가할 JSON 로그 파일 경로')
    parser.add_argument('--save', action='store_true', help='결과를 logs/eval/ 에 JSON으로 저장')
    args = parser.parse_args()
    evaluate(args.log, save=args.save)
