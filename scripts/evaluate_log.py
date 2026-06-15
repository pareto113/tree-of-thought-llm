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
from collections import defaultdict, Counter


def _parse_filename_meta(log_path: str) -> dict:
    """파일명에서 모델·온도·방법·퍼즐 범위를 추출한다."""
    stem = os.path.splitext(os.path.basename(log_path))[0]
    parts = stem.split('_')

    # 첫 번째 float 값이 temperature
    temp_idx = None
    for i, p in enumerate(parts):
        try:
            float(p)
            temp_idx = i
            break
        except ValueError:
            continue

    if temp_idx is None:
        return {}

    model = '_'.join(parts[:temp_idx])
    temperature = float(parts[temp_idx])

    start, end, method_parts = None, None, []
    for p in parts[temp_idx + 1:]:
        if p.startswith('start'):
            start = int(p[5:])
        elif p.startswith('end'):
            end = int(p[3:])
        else:
            method_parts.append(p)

    return {
        'model':         model,
        'temperature':   temperature,
        'method':        '_'.join(method_parts),
        'puzzle_range':  f'{start}-{end - 1}' if start is not None and end is not None else '?',
    }


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


# ── Step 실패 분석 헬퍼 ───────────────────────────────────────────

def _can_reach_24(nums: list, target: float = 24.0, tol: float = 1e-6) -> bool:
    """남은 숫자들로 사칙연산을 통해 target에 도달 가능한지 brute-force 검증."""
    if len(nums) == 1:
        return abs(nums[0] - target) < tol
    for i in range(len(nums)):
        for j in range(len(nums)):
            if i == j:
                continue
            a, b = nums[i], nums[j]
            rest = [nums[k] for k in range(len(nums)) if k != i and k != j]
            candidates = [a + b, a - b, a * b]
            if abs(b) > tol:
                candidates.append(a / b)
            for c in candidates:
                if _can_reach_24(rest + [c], target, tol):
                    return True
    return False


def _cot_failure_step(y: str):
    """CoT 출력 하나에서 첫 번째 실패 step 번호(1-indexed)를 반환.
    모든 step을 통과해 최종 답이 24이면 None 반환(정답).
    """
    lines = [l.strip() for l in y.strip().split('\n') if l.strip()]
    step = 0
    for line in lines:
        m = re.search(r'left:\s*([\d. ]+)\)', line)
        if not m:
            continue
        step += 1
        nums = [float(x) for x in m.group(1).strip().split()]
        if len(nums) == 1:
            return None if abs(nums[0] - 24) < 1e-6 else step
        if not _can_reach_24(nums):
            return step
    return step if step else None  # 파싱 불가


def _tot_failure_step(entry: dict):
    """ToT 로그 entry에서 첫 번째 실패 step 번호(1-indexed)를 반환.
    모든 step의 candidate 중 최소 하나가 살아있으면 None 반환(정답 후보 있음).
    """
    steps = entry.get('steps', [])
    for step_i, step in enumerate(steps, start=1):
        candidates = step.get('select_new_ys', [])
        reachable = False
        for y in candidates:
            last = y.strip().split('\n')[-1]
            m = re.search(r'left:\s*([\d. ]+)\)', last)
            if not m:
                continue
            nums = [float(x) for x in m.group(1).strip().split()]
            if len(nums) == 1:
                if abs(nums[0] - 24) < 1e-6:
                    return None  # 정답
            elif _can_reach_24(nums):
                reachable = True
                break
        if not reachable:
            return step_i
    return None


def _is_io_standard(data: list) -> bool:
    """IO standard 로그인지 확인: 출력에 'left:' 패턴이 없으면 IO standard."""
    for entry in data[:3]:
        for y in entry.get('ys', []):
            if re.search(r'left:\s*[\d. ]+\)', y):
                return False
    return True


def analyze_step_failures(data: list) -> dict:
    """Figure 3(b)용: step별 첫 실패 분포를 집계한다.

    ToT 전용 카테고리:
      - 1, 2, 3, ... : BFS 탐색이 해당 step에서 소멸 (search failure)
      - 'answer_fmt_error': BFS가 left=24에 도달했으나 Answer 표현식이 틀림 (ADR-0007)
      - 'correct': 최종 정답
    """
    is_tot = any('steps' in e and e['steps'] for e in data)

    # IO standard는 step 구조 없음 → 분석 불가
    if not is_tot and _is_io_standard(data):
        return {'n/a': 'IO standard format has no intermediate steps'}

    dist = defaultdict(int)

    for entry in data:
        if is_tot:
            fail = _tot_failure_step(entry)
            if fail is None:
                infos = entry.get('infos', [])
                if any(info.get('r') for info in infos):
                    fail = 'correct'
                else:
                    # BFS가 left=24에 도달했지만 최종 Answer 표현식이 틀림 (ADR-0007)
                    fail = 'answer_fmt_error'
        else:
            ys = entry.get('ys', [])
            for y in ys:
                fail = _cot_failure_step(y)
                dist[fail if fail is not None else 'correct'] += 1
            continue
        dist[fail] += 1

    n = sum(dist.values())

    def _sort_key(k):
        if isinstance(k, int):
            return (0, k)
        if k == 'answer_fmt_error':
            return (1, 0)
        return (2, 0)  # 'correct'

    sorted_items = sorted(dist.items(), key=lambda x: _sort_key(x[0]))
    return {
        'distribution': {str(k): v for k, v in sorted_items},
        'total': n,
        'rates': {str(k): round(v / n, 4) if n else 0 for k, v in sorted_items},
    }


def compute_nodes_visited(data: list) -> dict:
    """Figure 3(a)용: nodes_visited(퍼즐당 평균) 집계.

    nodes_visited = 전체 steps에서 len(new_ys) 합산 / 퍼즐 수
    논문 정의: 'number of partial solutions evaluated' (ADR-0007)
    """
    is_tot = any('steps' in e and e['steps'] for e in data)
    if not is_tot:
        # naive_run: 퍼즐당 n_generate_sample개 샘플 = nodes
        total = sum(len(e.get('ys', [])) for e in data)
        per_puzzle = total / len(data) if data else 0
        return {'total': total, 'per_puzzle': round(per_puzzle, 2), 'note': 'naive_run: nodes = n_generate_sample'}

    total = 0
    for entry in data:
        for step in entry.get('steps', []):
            total += len(step.get('new_ys', []))
    per_puzzle = total / len(data) if data else 0
    return {'total': total, 'per_puzzle': round(per_puzzle, 2)}


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
    is_io_std = _is_io_standard(data)
    cnt_avg = 0
    cnt_any = 0
    cnt_sc  = 0
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
        answers = [y.strip().split('\n')[-1] for y in ys]
        # CoT-SC: CoT 출력에만 적용 (IO standard는 SC 없음)
        if not is_io_std and answers:
            top_answer = Counter(answers).most_common(1)[0][0]
            top_correct = accs[answers.index(top_answer)] if answers.index(top_answer) < len(accs) else 0
            cnt_sc += int(top_correct)
        else:
            top_correct = 0
        if entry.get('x'):
            input_str = entry['x']
        elif entry.get('steps'):
            input_str = entry['steps'][0]['x']
        else:
            input_str = '?'
        results.append({
            'idx':     idx,
            'input':   input_str,
            'any':     any(accs),
            'avg':     sum(accs) / len(accs),
            'sc':      bool(top_correct),
            'accs':    accs,
            'answers': answers,
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
        # 정답(r=1)이 있으면 첫 번째 정답을 표시, 없으면 첫 번째 답 표시
        correct_idx = next((i for i, a in enumerate(r['accs']) if a == 1), None)
        ans = r['answers'][correct_idx] if correct_idx is not None else (r['answers'][0] if r['answers'] else '-')
        print(f"  {r['idx']:<6} {r['input']:<16} {mark:<6} {r['avg']:<8.3f}  {ans}")

    print(f"\n  cnt_avg (평균 정답률):    {cnt_avg/n_puzzles:.3f}")
    print(f"  cnt_any (best of k):      {cnt_any}/{n_puzzles} = {cnt_any/n_puzzles*100:.0f}%")
    if not is_io_std:
        print(f"  cnt_sc  (CoT-SC 최다득표): {cnt_sc}/{n_puzzles} = {cnt_sc/n_puzzles*100:.0f}%")

    # ── 3. Step 실패 분포 (Figure 3(b)) ──────────────────────────
    step_fail = analyze_step_failures(data)
    print(f"\n【 3. Step 실패 분포 (Figure 3(b)) 】")
    print(sep)
    if 'n/a' in step_fail:
        print(f"  {step_fail['n/a']}")
    else:
        for k, rate in step_fail['rates'].items():
            if k == 'correct':
                label = 'Correct'
            elif k == 'answer_fmt_error':
                label = 'Ans fmt err'
            else:
                label = f'Step {k}'
            print(f"  {label:<14}: {rate*100:.1f}%  ({step_fail['distribution'][k]}/{step_fail['total']})")
    print()

    # ── 4. Nodes visited (Figure 3(a)) ────────────────────────
    nodes = compute_nodes_visited(data)
    print(f"【 4. Nodes visited (Figure 3(a)) 】")
    print(sep)
    print(f"  총 nodes:        {nodes['total']:,}")
    print(f"  퍼즐당 평균:      {nodes['per_puzzle']}")
    if 'note' in nodes:
        print(f"  ({nodes['note']})")
    print()

    usage = data[-1].get('usage_so_far', {})
    if usage:
        print(f"\n  누적 토큰: prompt={usage.get('prompt_tokens',0):,} / "
              f"completion={usage.get('completion_tokens',0):,} / "
              f"cost=${usage.get('cost',0):.4f}")
    print()

    # ── JSON 저장 ─────────────────────────────────────────────────
    eval_data = {
        'source_log': log_path,
        'meta':       _parse_filename_meta(log_path),
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
            'cnt_avg':      round(cnt_avg / n_puzzles, 4),
            'cnt_any':      cnt_any,
            'cnt_any_rate': round(cnt_any / n_puzzles, 4),
            'cnt_sc':       None if is_io_std else cnt_sc,
            'cnt_sc_rate':  None if is_io_std else round(cnt_sc / n_puzzles, 4),
            'per_puzzle':   results,
        },
        'step_failures': step_fail,
        'nodes_visited': nodes,
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
