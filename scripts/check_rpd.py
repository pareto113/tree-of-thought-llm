#!/usr/bin/env python3
"""
RPD(Requests Per Day) 잔여량 확인 유틸리티.

gpt-4o-mini 등 일부 모델에만 적용되는 일별 요청 한도.
일반적인 RPM(분당)과 달리 실시간으로 천천히 보충되는 rolling window 방식.
매일 특정 시각에 일괄 리셋되지 않음.

주의: x-ratelimit-remaining-requests 헤더는 OpenAI 서버 상황에 따라
RPD 또는 RPM 값을 담을 수 있다. reset 시간에 'h'(시간)가 포함되면 RPD,
없으면 RPM으로 판단한다. RPM이 표시될 때는 RPD 잔여량을 알 수 없다.

사용법:
  python scripts/check_rpd.py                      # 잔여량 조회만
  python scripts/check_rpd.py --min 3000           # RPD 확인 시 3000 미만이면 종료(exit 1)
  python scripts/check_rpd.py --min 3000 --ask     # RPD 확인 시 3000 미만이면 사용자 확인
                                                    # RPM 표시 시 --min 유무와 관계없이 사용자 확인
"""
import argparse
import sys
import os

def check_rpd(min_required: int = 0, ask: bool = False) -> int:
    from dotenv import load_dotenv
    load_dotenv()
    import openai

    client = openai.OpenAI()
    resp = client.chat.completions.with_raw_response.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": "hi"}],
        max_tokens=1,
    )
    h = resp.headers
    remaining = int(h.get("x-ratelimit-remaining-requests", 0))
    limit = int(h.get("x-ratelimit-limit-requests", 0))
    reset = h.get("x-ratelimit-reset-requests", "unknown")

    # reset 시간에 'h'가 포함되면 RPD(rolling day), 없으면 RPM(per minute)
    kind = "RPD" if reset != "unknown" and "h" in reset else "RPM"

    print(f"Type      : {kind}")
    print(f"Remaining : {remaining:,} / {limit:,}")
    print(f"Reset in  : {reset}")

    if kind == "RPM":
        # RPM이 표시될 때는 RPD 잔여량을 알 수 없음 (헤더가 RPD를 보장하지 않음)
        if min_required > 0:
            print(f"\n⚠️  RPD 잔여량 확인 불가 (현재 헤더: RPM)")
            print("   RPD 상태를 알 수 없으므로 실험이 중간에 중단될 수 있습니다.")
            ans = input("   그래도 계속하겠습니까? [y/N] ").strip().lower()
            if ans != "y":
                print("중단합니다.")
                sys.exit(1)
        return remaining

    if min_required > 0 and remaining < min_required:
        print(f"\n⚠️  잔여 RPD({remaining:,})가 필요 추정량({min_required:,})보다 적습니다.")
        print("   실험이 중간에 중단될 수 있습니다.")
        if ask:
            ans = input("   그래도 계속하겠습니까? [y/N] ").strip().lower()
            if ans != "y":
                print("중단합니다.")
                sys.exit(1)
        else:
            sys.exit(1)

    return remaining


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--min", type=int, default=0,
                        help="이 값보다 RPD가 적으면 종료(exit 1)")
    parser.add_argument("--ask", action="store_true",
                        help="--min 조건 미충족 시 강제 종료 대신 사용자 확인 요청")
    args = parser.parse_args()
    check_rpd(min_required=args.min, ask=args.ask)
