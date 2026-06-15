#!/usr/bin/env bash
# 실험 6, 7, 8: ToT b=1~5 병렬 실행
# 사용법: bash scripts/run_tot_parallel.sh [START] [END]
#   START, END 생략 시 기본값 900, 1000
#
# RPD(Requests Per Day) 주의:
#   b=1~5 전체 실행 시 최대 ~22,600 API 호출. gpt-4o-mini 일일 한도 10,000건.
#   RPD는 rolling window 방식으로 실시간 보충됨 (특정 시각 일괄 리셋 아님).
#   한도 소진 시 실험이 중간에 중단되며, resume 로직으로 재개 가능.

set -e
cd "$(dirname "$0")/.."

# ── RPD 사전 확인 ──────────────────────────────────────────────────────────────
# 5개 실험 전체 완료 기준 ~22,600건이지만 하루 한도(10,000)를 항상 초과함.
# 3,000건 미만이면 진행해도 의미 있는 진척이 어려우므로 사용자 확인 요청.
echo "── RPD(Requests Per Day) 사전 확인 ──────────────────────"
python scripts/check_rpd.py --min 3000 --ask
echo "──────────────────────────────────────────────────────────"
echo ""

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

echo "ToT 병렬 실행 시작: puzzles $START–$END"
echo "로그: logs/run_tot_b{1..5}.log"
echo ""

# b=5 (실험 6)
nohup $BASE --n_select_sample 5 > logs/run_tot_b5.log 2>&1 &
PID_B5=$!

# b=1 (실험 7)
nohup $BASE --n_select_sample 1 > logs/run_tot_b1.log 2>&1 &
PID_B1=$!

# b=2, 3, 4 (실험 8)
nohup $BASE --n_select_sample 2 > logs/run_tot_b2.log 2>&1 &
PID_B2=$!

nohup $BASE --n_select_sample 3 > logs/run_tot_b3.log 2>&1 &
PID_B3=$!

nohup $BASE --n_select_sample 4 > logs/run_tot_b4.log 2>&1 &
PID_B4=$!

echo "PID b=1: $PID_B1"
echo "PID b=2: $PID_B2"
echo "PID b=3: $PID_B3"
echo "PID b=4: $PID_B4"
echo "PID b=5: $PID_B5"
echo ""
echo "진행 상황 확인:"
echo "  tail -1 logs/run_tot_b5.log"
echo "  tail -1 logs/run_tot_b{1..5}.log"
