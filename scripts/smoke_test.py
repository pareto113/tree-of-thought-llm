"""
GPT-4o mini 형식 준수 smoke test — 퍼즐 3개로 IO/CoT/ToT 출력 형식 확인.
Usage: python scripts/smoke_test.py
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from dotenv import load_dotenv
load_dotenv()

import re
from tot.models import gpt
from tot.prompts.game24 import standard_prompt, cot_prompt, propose_prompt, value_prompt

PUZZLES = ['4 4 6 8', '1 1 4 6', '2 3 8 9']

PROPOSE_RE = re.compile(
    r'^[\d.]+\s*[+\-*/]\s*[\d.]+\s*=\s*[\d.]+\s*\(left:\s*[\d. ]+\)\s*$'
)

def check_io(puzzle):
    out = gpt(standard_prompt.format(input=puzzle), model='gpt-4o-mini', n=3)
    ok = sum(1 for o in out if 'answer:' in o.lower() or '= 24' in o.lower())
    print(f'  IO  [{puzzle}] 형식 OK: {ok}/3')
    for o in out:
        print(f'    > {o.strip()[:80]}')

def check_cot(puzzle):
    out = gpt(cot_prompt.format(input=puzzle), model='gpt-4o-mini', n=3)
    ok = sum(1 for o in out if 'answer:' in o.lower())
    print(f'  CoT [{puzzle}] 형식 OK (Answer: 포함): {ok}/3')
    for o in out:
        print(f'    > {o.strip()[:120]}')

def check_propose(puzzle):
    out = gpt(propose_prompt.format(input=puzzle), model='gpt-4o-mini', n=1)
    lines = [l.strip() for l in out[0].split('\n') if l.strip()]
    ok = sum(1 for l in lines if PROPOSE_RE.match(l))
    print(f'  Propose [{puzzle}] 형식 OK: {ok}/{len(lines)} 줄')
    for l in lines:
        mark = '✅' if PROPOSE_RE.match(l) else '❌'
        print(f'    {mark} {l}')

def check_value(puzzle):
    prompt = value_prompt.split('{input}')[0] + puzzle
    out = gpt(prompt, model='gpt-4o-mini', n=3)
    ok = sum(1 for o in out if any(w in o.lower() for w in ['sure', 'likely', 'impossible']))
    print(f'  Value [{puzzle}] 형식 OK: {ok}/3')
    for o in out:
        print(f'    > {o.strip()[:80]}')

print('=' * 60)
print('GPT-4o mini smoke test')
print('=' * 60)

for puzzle in PUZZLES:
    print(f'\n[{puzzle}]')
    check_io(puzzle)
    check_cot(puzzle)
    check_propose(puzzle)
    check_value(puzzle)

print('\n완료. 형식 오류가 없으면 본 실험 진행 가능.')
