#!/usr/bin/env bash
# ToT b=1, 2, 3 재개 (RPD Day 1용 — ~7,100건)
# b=4는 완료, b=5는 Day 2에 별도 실행

set -e
cd "$(dirname "$0")/.."

START=${1:-900}
END=${2:-1000}

BASE="python run.py \
  --task game24 \
  --backend gpt-4o-mini \
  --method_generate propose \
  --n_generate_sample 1 \
  --method_evaluate value \
  --n_evaluate_sample 3 \
  --method_select greedy \
  --task_start_index $START \
  --task_end_index $END"

mkdir -p logs

echo "ToT b=1,2,3 재개: puzzles $START–$END"
echo ""

nohup $BASE --n_select_sample 1 > logs/run_tot_b1.log 2>&1 &
echo "PID b=1: $!"

nohup $BASE --n_select_sample 2 > logs/run_tot_b2.log 2>&1 &
echo "PID b=2: $!"

nohup $BASE --n_select_sample 3 > logs/run_tot_b3.log 2>&1 &
echo "PID b=3: $!"

echo ""
echo "진행 확인: python3 -c \""
echo "import json,os"
echo "for b in [1,2,3]:"
echo "  f=[x for x in os.listdir('logs/game24') if f'greedy{b}_start' in x and 'gpt-4o-mini' in x]"
echo "  if f: d=json.load(open(f'logs/game24/{f[0]}')); print(f'b={b}: {len(d)}/100')"
echo "\""
