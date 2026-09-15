#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""잔여 n · 예상 도달일 · 연장 종료일 제안 계산 CLI (표준 라이브러리만 사용).

dc 계약(dc-output-contract.md v1.0) D4a 2·3·4·5행이 쓰는 숫자를 재현 가능하게 만든다.

  - 군별 잔여 n = 필요 n − 누적 n (0 이하면 `도달`)
  - 군별 잔여 일수 = ceil(잔여 n ÷ 일 유입)  (일 유입이 0이거나 없으면 `확인 불가`)
  - 예상 도달일 = 기준일 + 잔여 일수 (가장 늦은 군이 실험 전체의 예상 도달일)
  - 최소 관찰 종료일 = 런칭일 + 최소 관찰 기간
  - 연장 종료일 제안 = max(예상 도달일, 최소 관찰 종료일)   ← dc §7-4
  - 원 종료일 대비 = 연장 종료일 제안 − 종료 예정일  (`{N}일 늦음` 형태로만 적는다)
  - --project: 현재 전환율이 그대로 유지될 때 필요 n에 도달한 시점의 z·stat-sig

⚠️ --project는 샘플 게이트 도달 후에만 돌린다 (dc §7-4). 도달 전 예상 유의성은 피킹의
   다른 이름이다 — 이 스크립트는 그 판단을 대신하지 않고, 호출한 쪽이 지킨다.

⚠️ 출력 셀의 첫 글자에 `=`·`+`를 쓰지 않는다 (dc §5 — 시트 수식 오인 방지).
"""

from __future__ import annotations

import argparse
import datetime
import json
import math
import sys
from typing import List, Optional

# statsig.py와 같은 정규분포 상수. 🚫 statsig.py를 import 하지 않는다 —
# 두 스크립트가 서로를 부르면 경로 의존이 생기므로 10줄을 다시 쓴다.
UNREACHABLE = "확인 불가"
REACHED = "도달"


# ---------------------------------------------------------------------------
# 통계 — statsig.py의 two_proportion_test(풀링 SE)와 같은 식을 다시 구현한다.
# ---------------------------------------------------------------------------


def normal_cdf(x: float) -> float:
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


def two_proportion_z(n1: int, x1: int, n2: int, x2: int) -> dict:
    """n1/x1 = 대조군, n2/x2 = 실험군. 풀링 SE로 z·양측 p·stat-sig(1−p)."""
    p1 = x1 / n1
    p2 = x2 / n2
    pooled = (x1 + x2) / (n1 + n2)
    se = math.sqrt(pooled * (1 - pooled) * (1 / n1 + 1 / n2))
    z = (p2 - p1) / se if se > 0 else 0.0
    p_two_sided = 2 * (1 - normal_cdf(abs(z)))
    return {
        "p1": p1,
        "p2": p2,
        "diff_pp": (p2 - p1) * 100,
        "z": z,
        "p_two_sided": p_two_sided,
        "statsig_pct": (1 - p_two_sided) * 100,
    }


def scale_counts(n: int, x: int, need_n: int) -> int:
    """현재 전환율을 유지한 채 필요 n까지 늘렸을 때의 전환 건수."""
    if n <= 0:
        return 0
    return int(round((x / n) * need_n))


def alpha_effective(alpha: float, bonferroni: Optional[int]) -> float:
    if bonferroni and bonferroni > 1:
        return alpha / bonferroni
    return alpha


# ---------------------------------------------------------------------------
# 도달 추정
# ---------------------------------------------------------------------------


def arm_label(index: int, total: int) -> str:
    if total == 1:
        return "군1"
    if index == 0:
        return "대조군"
    return "실험군{}".format(index)


def days_to_reach(remaining: int, daily: Optional[float]) -> Optional[int]:
    """잔여 일수(올림). 도달했으면 0, 일 유입이 없거나 0이면 None."""
    if remaining <= 0:
        return 0
    if daily is None or daily <= 0:
        return None
    return int(math.ceil(remaining / daily))


def estimate_arms(
    need_n: int,
    have: List[int],
    daily: Optional[List[float]],
    today: datetime.date,
) -> List[dict]:
    total = len(have)
    rows = []
    for i, cur in enumerate(have):
        d = None
        if daily:
            d = daily[i] if len(daily) > 1 else daily[0]
        remaining = need_n - cur
        n_days = days_to_reach(remaining, d)
        reach_date = None
        if n_days is not None:
            reach_date = today + datetime.timedelta(days=n_days)
        rows.append(
            {
                "군": arm_label(i, total),
                "누적_n": cur,
                "잔여_n": max(remaining, 0),
                "도달": remaining <= 0,
                "일_유입": d,
                "잔여_일수": n_days,
                "예상_도달일": reach_date,
            }
        )
    return rows


def latest_reach(rows: List[dict]) -> tuple:
    """(가장 늦은 예상 도달일, 확인 불가 군이 있는가)."""
    unknown = any(r["잔여_일수"] is None for r in rows)
    dates = [r["예상_도달일"] for r in rows if r["예상_도달일"] is not None]
    return (max(dates) if dates else None, unknown)


# ---------------------------------------------------------------------------
# 포맷터
# ---------------------------------------------------------------------------


def fmt_date(d: Optional[datetime.date]) -> str:
    return d.isoformat() if d else UNREACHABLE


def fmt_md(d: Optional[datetime.date]) -> str:
    return "{}/{}".format(d.month, d.day) if d else UNREACHABLE


def fmt_days(row: dict) -> str:
    if row["도달"]:
        return REACHED
    if row["잔여_일수"] is None:
        return UNREACHABLE
    return "{}일".format(row["잔여_일수"])


def fmt_remaining(row: dict) -> str:
    if row["도달"]:
        return REACHED
    return "{}명".format(row["잔여_n"])


def fmt_daily(row: dict) -> str:
    d = row["일_유입"]
    if d is None or d <= 0:
        return UNREACHABLE
    if float(d).is_integer():
        return "{:d}명/일".format(int(d))
    return "{:.1f}명/일".format(d)


def fmt_delta(delta_days: Optional[int]) -> str:
    """🚫 셀 첫 글자에 `+`를 쓰지 않는다 — `{N}일 늦음`으로 적는다 (dc §5)."""
    if delta_days is None:
        return UNREACHABLE
    if delta_days > 0:
        return "{}일 늦음".format(delta_days)
    if delta_days < 0:
        return "{}일 빠름".format(-delta_days)
    return "차이 없음"


def build_result(args: argparse.Namespace) -> dict:
    today = args.today
    rows = estimate_arms(args.need_n, args.have, args.daily, today)
    reach_date, unknown = latest_reach(rows)

    min_obs_end = None
    if args.launch is not None and args.min_days is not None:
        min_obs_end = args.launch + datetime.timedelta(days=args.min_days)

    candidates = [d for d in (reach_date, min_obs_end) if d is not None]
    proposed_end = max(candidates) if candidates and not unknown else (
        max(candidates) if candidates and reach_date is not None else None
    )
    if unknown and reach_date is None:
        proposed_end = None

    delta = None
    if proposed_end is not None and args.planned_end is not None:
        delta = (proposed_end - args.planned_end).days

    projection = None
    if args.project:
        nc, xc = args.control
        nt, xt = args.treatment
        sc = scale_counts(nc, xc, args.need_n)
        st = scale_counts(nt, xt, args.need_n)
        stats = two_proportion_z(args.need_n, sc, args.need_n, st)
        a_eff = alpha_effective(args.alpha, args.bonferroni)
        projection = {
            "가정": "현재 전환율 유지",
            "필요_n": args.need_n,
            "대조군_전환율": stats["p1"],
            "실험군_전환율": stats["p2"],
            "대조군_전환_추정": sc,
            "실험군_전환_추정": st,
            "차이_pp": stats["diff_pp"],
            "z": stats["z"],
            "p_양측": stats["p_two_sided"],
            "stat_sig_pct": stats["statsig_pct"],
            "alpha": args.alpha,
            "bonferroni": args.bonferroni,
            "alpha_eff": a_eff,
            "유의_임계_pct": (1 - a_eff) * 100,
            "유의_여부": stats["p_two_sided"] < a_eff,
        }

    return {
        "기준일": today,
        "필요_n": args.need_n,
        "군별": rows,
        "예상_도달일": reach_date,
        "일_유입_확인_불가_군": unknown,
        "런칭일": args.launch,
        "최소_관찰_기간": args.min_days,
        "최소_관찰_종료일": min_obs_end,
        "연장_종료일_제안": proposed_end,
        "원_종료일": args.planned_end,
        "원_종료일_대비_일": delta,
        "도달_시점_예상": projection,
    }


def format_md(result: dict) -> str:
    lines = []
    lines.append("### 잔여 n · 예상 도달일   [기준일 {}]".format(fmt_date(result["기준일"])))
    lines.append("")
    lines.append("| 군 | 누적 n | 잔여 n | 일 유입 | 잔여 일수 | 예상 도달일 |")
    lines.append("|---|---|---|---|---|---|")
    for r in result["군별"]:
        lines.append(
            "| {} | {} | {} | {} | {} | {} |".format(
                r["군"],
                r["누적_n"],
                fmt_remaining(r),
                fmt_daily(r),
                fmt_days(r),
                REACHED if r["도달"] else fmt_date(r["예상_도달일"]),
            )
        )
    lines.append("")
    lines.append("| 항목 | 값 |")
    lines.append("|---|---|")
    lines.append("| 필요 n (군당) | {} |".format(result["필요_n"]))
    lines.append(
        "| 예상 도달일 (가장 늦은 군) | {} |".format(fmt_date(result["예상_도달일"]))
    )
    lines.append(
        "| 최소 관찰 종료일 | {} |".format(fmt_date(result["최소_관찰_종료일"]))
    )
    lines.append(
        "| 연장 종료일 제안 | {} |".format(fmt_date(result["연장_종료일_제안"]))
    )
    lines.append(
        "| 원 종료일 | {} |".format(fmt_date(result["원_종료일"]))
    )
    lines.append(
        "| 원 종료일 대비 | {} |".format(fmt_delta(result["원_종료일_대비_일"]))
    )
    if result["일_유입_확인_불가_군"]:
        lines.append("")
        lines.append("- 일 유입을 받지 못한 군이 있어 그 군의 잔여 일수는 `확인 불가`입니다.")

    pj = result["도달_시점_예상"]
    if pj:
        lines.append("")
        lines.append("### 도달 시점 예상 (현재 전환율 유지 가정)   [샘플 게이트 도달 후에만]")
        lines.append("")
        lines.append("| 항목 | 값 |")
        lines.append("|---|---|")
        lines.append("| 가정 | 현재 전환율 유지 · 군당 n {} |".format(pj["필요_n"]))
        lines.append(
            "| 대조군 전환율 | {:.2f}% ({} / {}) |".format(
                pj["대조군_전환율"] * 100, pj["대조군_전환_추정"], pj["필요_n"]
            )
        )
        lines.append(
            "| 실험군 전환율 | {:.2f}% ({} / {}) |".format(
                pj["실험군_전환율"] * 100, pj["실험군_전환_추정"], pj["필요_n"]
            )
        )
        lines.append("| 절대 차이 | 절대 {:.2f}%p |".format(pj["차이_pp"]))
        lines.append("| z | {:.4f} |".format(pj["z"]))
        lines.append("| p(양측) | {:.6f} |".format(pj["p_양측"]))
        lines.append("| 도달 시점 예상 stat-sig | {:.1f}% |".format(pj["stat_sig_pct"]))
        lines.append(
            "| 유의 임계 (α {}{}) | {:.2f}% |".format(
                pj["alpha"],
                " · K={}".format(pj["bonferroni"]) if pj["bonferroni"] else "",
                pj["유의_임계_pct"],
            )
        )
        lines.append("| 임계 도달 여부 | {} |".format("예" if pj["유의_여부"] else "아니오"))
        lines.append("")
        lines.append("- 이 값은 **예상**이지 판정이 아닙니다 — 판정은 실측으로 다시 냅니다.")
    return "\n".join(lines)


def _jsonable(obj):
    if isinstance(obj, datetime.date):
        return obj.isoformat()
    if isinstance(obj, dict):
        return {k: _jsonable(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_jsonable(v) for v in obj]
    return obj


def format_json(result: dict) -> str:
    return json.dumps(_jsonable(result), ensure_ascii=False, indent=2)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def parse_date(value: str, flag: str) -> datetime.date:
    try:
        return datetime.datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError:
        _fail("{} 는 YYYY-MM-DD 형식이어야 합니다: {}".format(flag, value))


def _fail(message: str) -> None:
    sys.stderr.write("오류: {}\n".format(message))
    raise SystemExit(2)


def build_arg_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="잔여 n · 예상 도달일 · 연장 종료일 제안 계산 CLI (dc 계약 D4a 2·3·4·5행)."
    )
    p.add_argument("--need-n", type=int, required=True, help="군당 필요 n (설계서 전사값)")
    p.add_argument(
        "--have", type=int, nargs="+", required=True,
        help="군별 누적 n — 대조군부터 군 수만큼",
    )
    p.add_argument(
        "--daily", type=float, nargs="+",
        help="군별 일 유입 — 1개만 주면 전 군 공통. 없으면 잔여 일수가 `확인 불가`",
    )
    p.add_argument("--today", help="기준일 YYYY-MM-DD (없으면 오늘)")
    p.add_argument("--launch", help="런칭일 YYYY-MM-DD")
    p.add_argument("--min-days", type=int, help="최소 관찰 기간(일)")
    p.add_argument("--planned-end", help="설계서 종료 예정일 YYYY-MM-DD")
    p.add_argument(
        "--project", action="store_true",
        help="현재 전환율 유지 시 필요 n 도달 시점의 z·stat-sig (샘플 게이트 도달 후에만)",
    )
    p.add_argument("--control", type=int, nargs=2, metavar=("N", "X"), help="--project용 대조군 노출·전환")
    p.add_argument("--treatment", type=int, nargs=2, metavar=("N", "X"), help="--project용 실험군 노출·전환")
    p.add_argument("--alpha", type=float, default=0.05, help="유의수준 (기본 0.05)")
    p.add_argument("--bonferroni", type=int, help="다중비교 보정 계수 K")
    p.add_argument("--format", choices=["md", "json"], default="md")
    return p


def validate_and_normalize(args: argparse.Namespace) -> argparse.Namespace:
    if args.need_n <= 0:
        _fail("--need-n 은 1 이상이어야 합니다.")
    if any(v < 0 for v in args.have):
        _fail("--have 값은 0 이상이어야 합니다.")
    if args.daily is not None:
        if any(v < 0 for v in args.daily):
            _fail("--daily 값은 0 이상이어야 합니다.")
        if len(args.daily) not in (1, len(args.have)):
            _fail("--daily 는 1개이거나 --have 와 같은 개수여야 합니다.")
    args.today = parse_date(args.today, "--today") if args.today else datetime.date.today()
    args.launch = parse_date(args.launch, "--launch") if args.launch else None
    args.planned_end = parse_date(args.planned_end, "--planned-end") if args.planned_end else None
    if args.min_days is not None and args.min_days < 0:
        _fail("--min-days 는 0 이상이어야 합니다.")
    if args.project:
        if not args.control or not args.treatment:
            _fail("--project 에는 --control N X 와 --treatment N X 가 필요합니다.")
        if args.control[0] <= 0 or args.treatment[0] <= 0:
            _fail("--control/--treatment 의 노출수는 1 이상이어야 합니다.")
    if args.bonferroni is not None and args.bonferroni < 1:
        _fail("--bonferroni 는 1 이상이어야 합니다.")
    return args


def main() -> None:
    args = validate_and_normalize(build_arg_parser().parse_args())
    result = build_result(args)
    if args.format == "json":
        print(format_json(result))
    else:
        print(format_md(result))


if __name__ == "__main__":
    main()
