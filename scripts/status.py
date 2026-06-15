#!/usr/bin/env python3
"""
실험 완료 상태 확인.
Usage: python scripts/status.py
"""
import json
import os

LOG_DIR = "logs/game24"
TOTAL = 100

# 파일명 패턴 → 실험 레이블 매핑 (gpt-4o-mini / o4-mini만 추적)
EXPERIMENTS = [
    ("실험 1  IO×1",      "gpt-4o-mini_0.7_naive_standard_sample_1_"),
    ("실험 2  IO×100",    "gpt-4o-mini_0.7_naive_standard_sample_100_"),
    ("실험 3  CoT×1",     "gpt-4o-mini_0.7_naive_cot_sample_1_"),
    ("실험 4/5 CoT×100",  "gpt-4o-mini_0.7_naive_cot_sample_100_"),
    ("실험 7  ToT b=1",   "gpt-4o-mini_0.7_propose1_value3_greedy1_"),
    ("실험 8  ToT b=2",   "gpt-4o-mini_0.7_propose1_value3_greedy2_"),
    ("실험 8  ToT b=3",   "gpt-4o-mini_0.7_propose1_value3_greedy3_"),
    ("실험 8  ToT b=4",   "gpt-4o-mini_0.7_propose1_value3_greedy4_"),
    ("실험 6  ToT b=5",   "gpt-4o-mini_0.7_propose1_value3_greedy5_"),
    ("실험 9  o4-mini IO×1", "o4-mini_1.0_naive_standard_sample_1_"),
]

def find_log(prefix: str):
    for fname in os.listdir(LOG_DIR):
        if fname.startswith(prefix):
            return os.path.join(LOG_DIR, fname)
    return None

def main():
    print(f"{'실험':<20}  {'진행':<8}  상태")
    print("─" * 44)
    for label, prefix in EXPERIMENTS:
        path = find_log(prefix)
        if path is None:
            print(f"{label:<20}  {'없음':<8}  ⬜ 미시작")
            continue
        data = json.load(open(path))
        n = len(data)
        if n >= TOTAL:
            mark = "✅ 완료"
        else:
            mark = "⏳ 진행중"
        print(f"{label:<20}  {n:>3}/{TOTAL}     {mark}")

if __name__ == "__main__":
    main()
