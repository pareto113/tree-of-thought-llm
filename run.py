import os
import json
import time
import argparse
from datetime import timedelta
from dotenv import load_dotenv

load_dotenv()

from tot.tasks import get_task
from tot.methods.bfs import solve, naive_solve
from tot.models import gpt_usage


def _fmt_sec(sec: float) -> str:
    """초를 'Xh Ym Zs' 형태 문자열로 변환."""
    return str(timedelta(seconds=int(sec)))


def run(args):
    task = get_task(args.task)
    backend = args.backend
    if args.naive_run:
        file = f'./logs/{args.task}/{backend}_{args.temperature}_naive_{args.prompt_sample}_sample_{args.n_generate_sample}_start{args.task_start_index}_end{args.task_end_index}.json'
    else:
        file = f'./logs/{args.task}/{backend}_{args.temperature}_{args.method_generate}{args.n_generate_sample}_{args.method_evaluate}{args.n_evaluate_sample}_{args.method_select}{args.n_select_sample}_start{args.task_start_index}_end{args.task_end_index}.json'
    os.makedirs(os.path.dirname(file), exist_ok=True)

    # resume: 기존 로그 로드 및 완료된 idx 복원
    if os.path.exists(file) and os.path.getsize(file) > 0:
        with open(file) as f:
            logs = json.load(f)
        done = {entry['idx'] for entry in logs}
        cnt_avg = sum(sum(info['r'] for info in entry['infos']) / len(entry['infos']) for entry in logs)
        cnt_any = sum(any(info['r'] for info in entry['infos']) for entry in logs)
        print(f"[resume] 기존 로그 로드: {len(done)}개 퍼즐 완료, 재개합니다.\n")
    else:
        logs, done, cnt_avg, cnt_any = [], set(), 0, 0

    total = args.task_end_index - args.task_start_index
    run_start = time.time()
    puzzle_times = []

    for i in range(args.task_start_index, args.task_end_index):
        if i in done:
            continue
        puzzle_start = time.time()

        # solve
        x = task.get_input(i)
        if args.naive_run:
            ys, info = naive_solve(args, task, i)
        else:
            ys, info = solve(args, task, i)

        # log
        infos = [task.test_output(i, y) for y in ys]
        info.update({'idx': i, 'x': x, 'ys': ys, 'infos': infos, 'usage_so_far': gpt_usage(args.backend)})
        logs.append(info)
        with open(file, 'w') as f:
            json.dump(logs, f, indent=4)

        # timing
        elapsed_puzzle = time.time() - puzzle_start
        puzzle_times.append(elapsed_puzzle)
        completed = len(done) + len(puzzle_times)
        avg_per_puzzle = sum(puzzle_times) / len(puzzle_times)
        remaining = total - completed
        eta = avg_per_puzzle * remaining
        total_elapsed = time.time() - run_start

        # log main metric + timing
        accs = [info['r'] for info in infos]
        cnt_avg += sum(accs) / len(accs)
        cnt_any += any(accs)
        print(
            f"[{completed}/{total}] idx={i} | "
            f"sum(accs)={sum(accs)} cnt_avg={cnt_avg:.3f} cnt_any={cnt_any} | "
            f"puzzle={_fmt_sec(elapsed_puzzle)} avg={_fmt_sec(avg_per_puzzle)} "
            f"elapsed={_fmt_sec(total_elapsed)} ETA={_fmt_sec(eta)}\n"
        )

    n = args.task_end_index - args.task_start_index
    print(cnt_avg / n, cnt_any / n)
    print('usage_so_far', gpt_usage(args.backend))
    print(f'total_time={_fmt_sec(time.time() - run_start)}')


def parse_args():
    args = argparse.ArgumentParser()
    args.add_argument('--backend', type=str, choices=['gpt-4o-mini', 'gpt-4o', 'gpt-4', 'gpt-3.5-turbo', 'o4-mini'], default='gpt-4o-mini')
    args.add_argument('--temperature', type=float, default=0.7)

    args.add_argument('--task', type=str, required=True, choices=['game24', 'text', 'crosswords'])
    args.add_argument('--task_start_index', type=int, default=900)
    args.add_argument('--task_end_index', type=int, default=1000)

    args.add_argument('--naive_run', action='store_true')
    args.add_argument('--prompt_sample', type=str, choices=['standard', 'cot'])  # only used when method_generate = sample, or naive_run

    args.add_argument('--method_generate', type=str, choices=['sample', 'propose'])
    args.add_argument('--method_evaluate', type=str, choices=['value', 'vote'])
    args.add_argument('--method_select', type=str, choices=['sample', 'greedy'], default='greedy')
    args.add_argument('--n_generate_sample', type=int, default=1)  # only thing needed if naive_run
    args.add_argument('--n_evaluate_sample', type=int, default=1)
    args.add_argument('--n_select_sample', type=int, default=1)

    args = args.parse_args()
    return args


if __name__ == '__main__':
    args = parse_args()
    print(args)
    run(args)