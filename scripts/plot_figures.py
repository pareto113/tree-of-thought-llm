#!/usr/bin/env python3
"""
논문 Figure 3 재현 플로팅 스크립트.
Usage: python scripts/plot_figures.py

출력:
  figures/figure3.png          — Figure 3(a) + 3(b) 나란히 배치 (300 dpi)
  figures/figure_b_breakdown.png — b값별 성공/오류 분포 (추가 그래프)
"""

import json
import os
import sys

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from evaluate_log import compute_nodes_visited, analyze_step_failures

LOG_DIR    = "logs/game24"
OUTPUT_DIR = "figures"
os.makedirs(OUTPUT_DIR, exist_ok=True)

# ── 스타일 설정 ───────────────────────────────────────────────────
plt.rcParams.update({
    'font.family':    'serif',
    'font.size':      10,
    'axes.linewidth': 0.8,
    'xtick.major.width': 0.8,
    'ytick.major.width': 0.8,
})

COLOR_IO  = '#5B7B9A'   # muted blue-gray
COLOR_COT = '#C97C5D'   # muted warm brown
COLOR_TOT = '#6A9B7E'   # muted teal-green


# ── 헬퍼 ──────────────────────────────────────────────────────────

def load_log(fname):
    with open(os.path.join(LOG_DIR, fname)) as f:
        return json.load(f)


def best_of_k_curve(data):
    """k=1...max_k 각각에 대해 best-of-k 성공률 곡선을 반환한다.

    Returns (ks, rates): 각 k에서의 성공률 배열.
    """
    max_k = max(len(e.get('infos', [])) for e in data)
    n     = len(data)
    rates = []
    for k in range(1, max_k + 1):
        successes = sum(
            int(any(info['r'] for info in e['infos'][:k]))
            for e in data
        )
        rates.append(successes / n)
    return list(range(1, max_k + 1)), rates


# ── Figure 3(a) 데이터 ────────────────────────────────────────────

def get_figure3a_data():
    io_data  = load_log("gpt-4o-mini_0.7_naive_standard_sample_100_start900_end1000.json")
    cot_data = load_log("gpt-4o-mini_0.7_naive_cot_sample_100_start900_end1000.json")

    io_ks,  io_rates  = best_of_k_curve(io_data)
    cot_ks, cot_rates = best_of_k_curve(cot_data)

    # ToT b=1~5: (nodes/puzzle, success_rate) — collect_results.py 기준
    tot_points = [
        (37.6,  0.26),   # b=1
        (56.7,  0.27),   # b=2
        (74.8,  0.44),   # b=3
        (93.6,  0.52),   # b=4
        (111.6, 0.60),   # b=5
    ]
    return io_ks, io_rates, cot_ks, cot_rates, tot_points


# ── Figure 3(b) 데이터 ────────────────────────────────────────────

def get_figure3b_data():
    # CoT: step 분석 결과 + answer_fmt_error 보정 (diagnose_cot_correct.py 결과)
    cot_bars = {
        'Step 1':   0.61,
        'Step 2':   0.30,
        'Step 3':   0.02,
        'Ans. fmt': 0.03,
        'Correct':  0.04,
    }
    # ToT b=5: analyze_step_failures 결과
    tot_bars = {
        'Step 1':   0.03,
        'Step 2':   0.12,
        'Step 3':   0.01,
        'Ans. fmt': 0.24,
        'Correct':  0.60,
    }
    return cot_bars, tot_bars


# ── b별 stacked bar 데이터 ────────────────────────────────────────

def get_b_breakdown_data():
    """b=1~5 각 ToT 실험의 성공/ans_fmt_error/step_fail 분포를 로그에서 추출."""
    fnames = [
        "gpt-4o-mini_0.7_propose1_value3_greedy1_start900_end1000.json",
        "gpt-4o-mini_0.7_propose1_value3_greedy2_start900_end1000.json",
        "gpt-4o-mini_0.7_propose1_value3_greedy3_start900_end1000.json",
        "gpt-4o-mini_0.7_propose1_value3_greedy4_start900_end1000.json",
        "gpt-4o-mini_0.7_propose1_value3_greedy5_start900_end1000.json",
    ]
    rows = []
    for fname in fnames:
        data = load_log(fname)
        sf   = analyze_step_failures(data)
        dist = sf['distribution']
        n    = sf['total']
        correct   = int(dist.get('correct', 0)) / n
        ans_fmt   = int(dist.get('answer_fmt_error', 0)) / n
        step_fail = 1.0 - correct - ans_fmt
        rows.append((correct, ans_fmt, step_fail))
    return rows


# ── 플로팅 ────────────────────────────────────────────────────────

def plot_figure3a():
    io_ks, io_rates, cot_ks, cot_rates, tot_points = get_figure3a_data()

    fig, ax = plt.subplots(figsize=(5, 4))

    ax.plot(io_ks, io_rates, color=COLOR_IO,  linewidth=1.5, label='IO (best of k)')
    ax.plot(cot_ks, cot_rates, color=COLOR_COT, linewidth=1.5, label='CoT (best of k)')

    tot_x = [p[0] for p in tot_points]
    tot_y = [p[1] for p in tot_points]
    ax.plot(tot_x, tot_y,
            color=COLOR_TOT, linewidth=1.5, linestyle='--',
            marker='o', markersize=5, label='ToT (b=1…5)')

    ax.set_xlim(0, 120)
    ax.set_ylim(0.0, 0.7)
    ax.set_yticks([0.0, 0.2, 0.4, 0.6])
    ax.set_xlabel('# nodes visited', fontsize=10)
    ax.set_ylabel('Rate solved', fontsize=10)
    ax.set_title('(a) Success rate with nodes visited', fontsize=10)
    ax.legend(loc='lower right', frameon=True, framealpha=0.8, fontsize=9)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)

    out = os.path.join(OUTPUT_DIR, 'figure3a.png')
    fig.savefig(out, dpi=300, bbox_inches='tight')
    plt.close(fig)
    print(f"저장 완료: {out}")


def plot_figure3b():
    cot_bars, tot_bars = get_figure3b_data()

    fig, ax = plt.subplots(figsize=(5, 4))

    categories = list(cot_bars.keys())
    x     = np.arange(len(categories))
    width = 0.35

    ax.bar(x - width/2, list(cot_bars.values()), width,
           color=COLOR_COT, label='CoT')
    ax.bar(x + width/2, list(tot_bars.values()), width,
           color=COLOR_TOT, label='ToT (b=5)')

    ax.set_xlim(-0.5, len(categories) - 0.5)
    ax.set_ylim(0.0, 0.7)
    ax.set_yticks([0.0, 0.2, 0.4, 0.6])
    ax.set_xticks(x)
    ax.set_xticklabels(categories, fontsize=9)
    ax.set_ylabel('Rate of samples', fontsize=10)
    ax.set_title('(b) Samples failed at each step', fontsize=10)
    ax.legend(loc='upper right', frameon=True, framealpha=0.8, fontsize=9)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)

    out = os.path.join(OUTPUT_DIR, 'figure3b.png')
    fig.savefig(out, dpi=300, bbox_inches='tight')
    plt.close(fig)
    print(f"저장 완료: {out}")


def plot_b_breakdown():
    rows = get_b_breakdown_data()
    b_vals = [1, 2, 3, 4, 5]

    correct   = [r[0] for r in rows]
    ans_fmt   = [r[1] for r in rows]
    step_fail = [r[2] for r in rows]

    fig, ax = plt.subplots(figsize=(6, 4))
    x = np.arange(len(b_vals))

    ax.bar(x, step_fail, label='Step failure',      color='#C0C0C0')
    ax.bar(x, ans_fmt,   label='Ans. fmt error',    color='#F4A460',
           bottom=step_fail)
    ax.bar(x, correct,   label='Correct',           color=COLOR_TOT,
           bottom=[step_fail[i] + ans_fmt[i] for i in range(len(b_vals))])

    ax.set_xticks(x)
    ax.set_xticklabels([f'b={b}' for b in b_vals])
    ax.set_ylim(0, 1.05)
    ax.set_yticks([0.0, 0.2, 0.4, 0.6, 0.8, 1.0])
    ax.set_ylabel('Proportion', fontsize=10)
    ax.set_title('Outcome breakdown by beam width (ToT, GPT-4o mini)', fontsize=10)
    ax.legend(loc='upper left', frameon=True, framealpha=0.8, fontsize=9)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)

    out = os.path.join(OUTPUT_DIR, 'figure_b_breakdown.png')
    fig.savefig(out, dpi=300, bbox_inches='tight')
    plt.close(fig)
    print(f"저장 완료: {out}")


if __name__ == '__main__':
    print("Figure 3(a) 생성 중...")
    plot_figure3a()
    print("Figure 3(b) 생성 중...")
    plot_figure3b()
    print("b별 breakdown 그래프 생성 중...")
    plot_b_breakdown()
    print("완료.")
