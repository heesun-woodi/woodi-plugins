#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""실험 모니터링용 통계 유의성 계산 CLI — 표준 라이브러리만 사용한다.

두 비율(대조군 vs 실험군, 반복 시 실험군 여러 개)의 z검정·95% CI(미풀링)·
베이지안 P(실험군>대조군)·SRM(표본비율불일치) 카이제곱·피킹 게이트·판정을
한 번에 계산해 markdown 표 또는 JSON으로 출력한다.

사용 예:
    python3 statsig.py --control 886 171 --treatment 909 185 \
        --gate-n 770 --format both

핵심 원칙(계약 §7-6·§7-7·§7-11):
    - 피킹 게이트: --gate-n 또는 --min-days 미충족이면 mode=health로
      전환하고 판정 관련 필드를 전부 마스킹한다(--force-verdict로만 강제
      해제 가능, 붉은 경고 필수).
    - SRM 우선: srm_flag=alarm이면 게이트 도달 여부와 무관하게 판정 필드를
      마스킹하고, mode=verdict일 때만 verdict를 DESIGN_FAULT_SRM으로 채운다
      (--force-verdict로도 해제되지 않는다).
    - KB09 예시 1((886,171)/(909,185) → p≈0.61·CI[-2.65,+4.73]·71%)과는
      부합하지만, KB09 예시 2·3의 기재값(p 0.07/0.09, 93%/96%)은 이 스크립트의
      공식으로 재현되지 않는다 — 오라클로 쓰지 않는다.

python3 표준 라이브러리만 사용한다 (pip 설치·venv 불요). 네트워크 접근 없음,
--out을 지정한 경우에만 파일에 쓴다.
"""
from __future__ import annotations

import argparse
import datetime
import json
import math
import random
import sys
from typing import Optional

# ---------------------------------------------------------------------------
# 상수 — ⚠️확인필요 표시된 값은 코치 확정 전까지의 잠정값이다.
# ---------------------------------------------------------------------------

Z_95 = 1.959963985425836  # 95% 양측 정규분포 임계값 (수학적으로 고정, 코치 확인 불필요)

# ⚠️확인필요 — 코치 확정: SRM p-value 임계 (ok >=0.01, warn 0.001~0.01, alarm <0.001)
SRM_P_WARN = 0.01
SRM_P_ALARM = 0.001

# ⚠️확인필요 — 코치 확정: 판정 statsig% 임계값. WIN/LOSE는 (1-alpha_effective)*100로
# 대체되므로(§ compute_alpha_effective), 아래 95.0은 --alpha 0.05 기본값일 때의 값이다.
STATSIG_WIN_PCT_DEFAULT = 95.0
STATSIG_CONTINUE_PCT = 80.0

DEFAULT_ALPHA = 0.05
DEFAULT_SEED = 20260907
DEFAULT_DRAWS = 200000

GATE_NUMERIC_FIELDS = (
    "diff_pp",
    "lift_rel_pct",
    "z",
    "p_two_sided",
    "statsig_pct",
    "ci95_lo_pp",
    "ci95_hi_pp",
    "bayes_p_treatment_better",
    "mde_met",
    "verdict",
)


# ---------------------------------------------------------------------------
# 정규분포 / 두 비율 z검정
# ---------------------------------------------------------------------------


def normal_cdf(x: float) -> float:
    return 0.5 * (1 + math.erf(x / math.sqrt(2)))


def two_proportion_test(n1: int, x1: int, n2: int, x2: int) -> dict:
    """n1/x1=대조군, n2/x2=실험군. 풀링 SE로 z·p, 미풀링 SE로 95% CI."""
    p1 = x1 / n1
    p2 = x2 / n2
    pooled = (x1 + x2) / (n1 + n2)
    se_pooled = math.sqrt(pooled * (1 - pooled) * (1 / n1 + 1 / n2))
    z = (p2 - p1) / se_pooled if se_pooled > 0 else 0.0
    p_two_sided = 2 * (1 - normal_cdf(abs(z)))

    se_unpooled = math.sqrt(p1 * (1 - p1) / n1 + p2 * (1 - p2) / n2)
    diff = p2 - p1
    ci_lo_pp = (diff - Z_95 * se_unpooled) * 100
    ci_hi_pp = (diff + Z_95 * se_unpooled) * 100

    statsig_pct = (1 - p_two_sided) * 100
    lift_rel_pct = (p2 - p1) / p1 * 100 if p1 != 0 else None

    return {
        "p1": p1,
        "p2": p2,
        "diff_ratio": diff,
        "diff_pp": diff * 100,
        "z": z,
        "p_two_sided": p_two_sided,
        "ci_lo_pp": ci_lo_pp,
        "ci_hi_pp": ci_hi_pp,
        "statsig_pct": statsig_pct,
        "lift_rel_pct": lift_rel_pct,
    }


# ---------------------------------------------------------------------------
# 정규화 상부 불완전감마함수 Q(a,x) — Numerical Recipes gammq 방식.
# math.lgamma(표준 라이브러리)로 로그공간 계산, df=1일 때 erfc(sqrt(x/2))와 일치.
# ---------------------------------------------------------------------------


def _gser(a: float, x: float, itmax: int = 200, eps: float = 3e-9) -> float:
    """급수 전개로 정규화 하부 불완전감마함수 P(a,x)를 구한다 (x < a+1 구간용)."""
    gln = math.lgamma(a)
    if x <= 0:
        return 0.0
    ap = a
    summ = 1.0 / a
    delta = summ
    for _ in range(itmax):
        ap += 1
        delta *= x / ap
        summ += delta
        if abs(delta) < abs(summ) * eps:
            break
    return summ * math.exp(-x + a * math.log(x) - gln)


def _gcf(a: float, x: float, itmax: int = 200, eps: float = 3e-9, fpmin: float = 1e-300) -> float:
    """연분수 전개로 정규화 상부 불완전감마함수 Q(a,x)를 구한다 (x >= a+1 구간용)."""
    gln = math.lgamma(a)
    b = x + 1.0 - a
    c = 1.0 / fpmin
    d = 1.0 / b
    h = d
    for i in range(1, itmax + 1):
        an = -i * (i - a)
        b += 2.0
        d = an * d + b
        if abs(d) < fpmin:
            d = fpmin
        c = b + an / c
        if abs(c) < fpmin:
            c = fpmin
        d = 1.0 / d
        delta = d * c
        h *= delta
        if abs(delta - 1.0) < eps:
            break
    return math.exp(-x + a * math.log(x) - gln) * h


def gammq(a: float, x: float) -> float:
    """정규화 상부 불완전감마함수 Q(a,x). a>0, x>=0."""
    if x < 0 or a <= 0:
        raise ValueError("gammq: a>0, x>=0 이어야 합니다.")
    if x == 0:
        return 1.0
    if x < a + 1.0:
        return 1.0 - _gser(a, x)
    return _gcf(a, x)


# ---------------------------------------------------------------------------
# SRM (표본비율불일치) — 카이제곱 적합도 검정
# ---------------------------------------------------------------------------


def chi_square_srm(observed: list, ratio: list) -> tuple:
    """observed=군별 노출수, ratio=설계 분배 비율(스케일 무관, 내부에서 정규화).

    반환: (chi2, df, p, flag)
    """
    total = sum(observed)
    ratio_sum = sum(ratio)
    normalized = [r / ratio_sum for r in ratio]
    expected = [total * r for r in normalized]
    chi2 = sum((o - e) ** 2 / e for o, e in zip(observed, expected))
    df = len(observed) - 1
    p = gammq(df / 2, chi2 / 2) if df > 0 else 1.0
    flag = srm_flag_from_p(p)
    return chi2, df, p, flag


def srm_flag_from_p(p: float) -> str:
    if p < SRM_P_ALARM:
        return "alarm"
    if p < SRM_P_WARN:
        return "warn"
    return "ok"


# ---------------------------------------------------------------------------
# 베이지안 P(실험군 > 대조군) — 사후분포 Beta(1+X, 1+N-X)
# ---------------------------------------------------------------------------


def bayes_prob_treatment_better_mc(
    nc: int, xc: int, nt: int, xt: int, seed: int = DEFAULT_SEED, draws: int = DEFAULT_DRAWS
) -> float:
    rng = random.Random(seed)
    count = 0
    alpha_c, beta_c = 1 + xc, 1 + (nc - xc)
    alpha_t, beta_t = 1 + xt, 1 + (nt - xt)
    for _ in range(draws):
        c = rng.betavariate(alpha_c, beta_c)
        t = rng.betavariate(alpha_t, beta_t)
        if t > c:
            count += 1
    return count / draws


def _log_beta(a: float, b: float) -> float:
    return math.lgamma(a) + math.lgamma(b) - math.lgamma(a + b)


def bayes_prob_treatment_better_integrate(nc: int, xc: int, nt: int, xt: int) -> float:
    """Evan Miller 닫힌 형 합 — control을 A, treatment를 B로 두고 P(A<B)를 구한다.

    P = Σ_{i=0}^{alphaB-1} B(alphaA+i, betaA+betaB) / [(betaB+i)·B(1+i, betaB)·B(alphaA, betaA)]
    """
    alpha_a, beta_a = 1 + xc, 1 + (nc - xc)
    alpha_b, beta_b = 1 + xt, 1 + (nt - xt)
    log_beta_a = _log_beta(alpha_a, beta_a)
    total = 0.0
    for i in range(alpha_b):
        term = math.exp(
            _log_beta(alpha_a + i, beta_a + beta_b) - _log_beta(1 + i, beta_b) - log_beta_a
        ) / (beta_b + i)
        total += term
    return total


# ---------------------------------------------------------------------------
# MDE 달성 / 다중비교 보정 / 판정 / 피킹 게이트
# ---------------------------------------------------------------------------


def compute_mde_met(
    diff_ratio: float, mde_abs: Optional[float], mde_rel: Optional[float], baseline: Optional[float]
) -> Optional[bool]:
    if mde_abs is not None:
        return diff_ratio >= mde_abs
    if mde_rel is not None and baseline is not None:
        return diff_ratio >= baseline * mde_rel
    return None


def compute_alpha_effective(alpha: float, bonferroni: Optional[int]) -> float:
    if bonferroni:
        return alpha / bonferroni
    return alpha


def determine_verdict(
    statsig_pct: float,
    diff_pp: float,
    mde_met: Optional[bool],
    win_threshold_pct: float,
    continue_threshold_pct: float,
) -> str:
    if statsig_pct >= win_threshold_pct:
        if diff_pp > 0:
            if mde_met is False:
                return "INCONCLUSIVE"
            return "WIN"
        if diff_pp < 0:
            return "LOSE"
        return "INCONCLUSIVE"
    if statsig_pct >= continue_threshold_pct:
        return "CONTINUE_80"
    return "INCONCLUSIVE"


def evaluate_gate(
    observed_ns: list, gate_n: Optional[int], min_days: Optional[int], days_elapsed: Optional[int]
) -> tuple:
    """(gate_reached, reason). reason은 "gate_n"/"min_days" 중 먼저 걸린 것."""
    reached = True
    reason = None
    if gate_n is not None and any(n < gate_n for n in observed_ns):
        reached = False
        reason = "gate_n"
    if min_days is not None and days_elapsed is not None and days_elapsed < min_days:
        reached = False
        reason = reason or "min_days"
    return reached, reason


# ---------------------------------------------------------------------------
# 포맷팅 헬퍼 — 셀 첫 글자에 '=' · '+' 사용 금지, p<0.0001은 "<0.0001"
# ---------------------------------------------------------------------------


def _fmt_ratio(value: Optional[float], decimals: int = 2) -> str:
    if value is None:
        return "—"
    return f"{value:.{decimals}f}"


def _fmt_pct(value: Optional[float], decimals: int = 2) -> str:
    """라벨에서 빠진 '%' 단위를 값 쪽에 붙인다 (계약 §3-8 M5b 행 이름과 정합)."""
    if value is None:
        return "—"
    return f"{value:.{decimals}f}%"


def _fmt_p(value: Optional[float]) -> str:
    if value is None:
        return "—"
    if value < 0.0001:
        return "<0.0001"
    return f"{value:.4f}"


def _fmt_bool(value: Optional[bool]) -> str:
    if value is None:
        return "—"
    return "달성" if value else "미달"


def _fmt_verdict(value: Optional[str]) -> str:
    return value if value else "—"


# ---------------------------------------------------------------------------
# 인자 파서
# ---------------------------------------------------------------------------


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="두 비율(대조군 vs 실험군) 통계 유의성·SRM·베이지안·피킹 게이트 계산 CLI."
    )
    parser.add_argument(
        "--control", required=True, nargs=2, type=int, metavar=("N", "X"),
        help="대조군 노출수 N, 전환수 X",
    )
    parser.add_argument(
        "--treatment", action="append", nargs=2, type=int, metavar=("N", "X"),
        help="실험군 노출수 N, 전환수 X (반복 지정 가능, 각각 대조군과 1:1 비교, 최소 1개 필수)",
    )
    parser.add_argument(
        "--ratio", nargs="+", type=float, default=None,
        help="설계 분배 비율 — 대조군부터 군 수만큼, 예: 50 50 (합이 100/1이 아니면 자동 정규화)",
    )
    parser.add_argument("--gate-n", type=int, default=None, help="피킹 게이트: 군별 최소 노출수")
    parser.add_argument("--min-days", type=int, default=None, help="피킹 게이트: 최소 경과일")
    parser.add_argument("--launch", type=str, default=None, help="실험 시작일 YYYY-MM-DD")
    parser.add_argument("--today", type=str, default=None, help="기준일 YYYY-MM-DD")
    parser.add_argument("--mde-abs", type=float, default=None, help="절대 MDE (비율, 예: 0.066=6.6%%p)")
    parser.add_argument("--mde-rel", type=float, default=None, help="상대 MDE (비율, --baseline 필수)")
    parser.add_argument("--baseline", type=float, default=None, help="--mde-rel용 기준 전환율 (비율)")
    parser.add_argument("--alpha", type=float, default=DEFAULT_ALPHA, help="유의수준 (기본 0.05)")
    parser.add_argument("--bonferroni", type=int, default=None, help="다중비교 보정 계수 K")
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED, help="베이지안 mc 난수 시드")
    parser.add_argument("--draws", type=int, default=DEFAULT_DRAWS, help="베이지안 mc 샘플 수")
    parser.add_argument("--bayes-method", choices=["mc", "integrate"], default="mc")
    parser.add_argument("--label-control", type=str, default="대조군")
    parser.add_argument("--label-treatment", type=str, default="실험군")
    parser.add_argument("--format", choices=["md", "json", "both"], default="md")
    parser.add_argument("--out", type=str, default=None, help="JSON 결과를 저장할 파일 경로")
    parser.add_argument(
        "--force-verdict", action="store_true",
        help="피킹 게이트 미달이어도 verdict 모드로 강제 계산 (SRM alarm은 해제되지 않음)",
    )
    return parser


def _fail(message: str) -> None:
    print(message, file=sys.stderr)
    raise SystemExit(2)


def validate_args(args: argparse.Namespace, n_arms: int) -> None:
    if not args.treatment:
        _fail("실험군 --treatment N X 를 최소 1개 지정하세요")
    if args.mde_abs is not None and args.mde_rel is not None:
        _fail("--mde-abs와 --mde-rel은 동시에 지정할 수 없습니다.")
    if args.mde_rel is not None and args.baseline is None:
        _fail("--mde-rel 사용 시 --baseline이 필요합니다.")
    min_days_group = (args.min_days, args.launch, args.today)
    if any(v is not None for v in min_days_group) and not all(v is not None for v in min_days_group):
        _fail("--min-days는 --launch --today와 함께 지정해야 합니다.")
    if args.ratio is not None and len(args.ratio) != n_arms:
        _fail(f"--ratio는 군 수({n_arms}개, 대조군+실험군)와 같은 개수를 지정해야 합니다.")
    if args.ratio is not None and sum(args.ratio) <= 0:
        _fail("--ratio 값의 합은 0보다 커야 합니다.")
    if args.draws is not None and args.draws < 1:
        _fail("--draws는 1 이상이어야 합니다.")
    if args.bonferroni is not None and args.bonferroni < 1:
        _fail("--bonferroni는 1 이상의 정수여야 합니다.")

    groups = [("대조군", args.control[0], args.control[1])]
    single = len(args.treatment) == 1
    for i, (n, x) in enumerate(args.treatment, start=1):
        label = "실험군" if single else f"실험군{i}"
        groups.append((label, n, x))
    for label, n, x in groups:
        if n <= 0:
            _fail(f"{label} 노출수 N은 1 이상이어야 합니다: N={n}")
        if x < 0 or x > n:
            _fail(f"{label} 전환수 X는 0 이상 N 이하여야 합니다: N={n} X={x}")


def parse_date(value: str, flag_name: str) -> datetime.date:
    try:
        return datetime.date.fromisoformat(value)
    except ValueError:
        _fail(f"{flag_name} 날짜 형식이 올바르지 않습니다 (YYYY-MM-DD): {value}")


# ---------------------------------------------------------------------------
# 결과 조립
# ---------------------------------------------------------------------------


def build_result(args: argparse.Namespace) -> dict:
    if not args.treatment:
        _fail("실험군 --treatment N X 를 최소 1개 지정하세요")
    n_arms = 1 + len(args.treatment)
    validate_args(args, n_arms)

    control_n, control_x = args.control
    treatments_raw = args.treatment  # list of [n, x]

    if len(treatments_raw) == 1:
        treatment_labels = [args.label_treatment]
    else:
        treatment_labels = [f"{args.label_treatment}{i + 1}" for i in range(len(treatments_raw))]

    observed = [control_n] + [n for n, _ in treatments_raw]
    ratio = args.ratio if args.ratio is not None else [1.0] * n_arms

    chi2, df, srm_p, srm_flag = chi_square_srm(observed, ratio)
    ratio_sum = sum(ratio)
    design_ratio = [r / ratio_sum for r in ratio]
    observed_ratio = [n / sum(observed) for n in observed]

    days_elapsed = None
    if args.launch is not None and args.today is not None:
        launch_date = parse_date(args.launch, "--launch")
        today_date = parse_date(args.today, "--today")
        days_elapsed = (today_date - launch_date).days

    gate_reached, _gate_reason = evaluate_gate(observed, args.gate_n, args.min_days, days_elapsed)

    force_applied = bool(args.force_verdict and not gate_reached)
    mode = "verdict" if (gate_reached or args.force_verdict) else "health"

    if srm_flag == "alarm":
        suppressed_reason = "SRM"
    elif not gate_reached:
        suppressed_reason = "gate"
    else:
        suppressed_reason = None

    should_mask = (srm_flag == "alarm") or (mode == "health")

    alpha_effective = compute_alpha_effective(args.alpha, args.bonferroni)
    win_threshold_pct = (1 - alpha_effective) * 100

    # 다중비교 보정 게이트 (계약 §3-8): 판정 군 수(실험군)가 2개 이상인데
    # --bonferroni 미지정이면 통계값은 유지하되 verdict만 마스킹한다.
    needs_bonferroni_warning = len(treatments_raw) >= 2 and args.bonferroni is None
    if args.bonferroni:
        multiple_comparison_label = f"Bonferroni α={alpha_effective:.4f}({args.bonferroni}비교)"
    elif len(treatments_raw) < 2:
        multiple_comparison_label = "해당 없음(2군)"
    else:
        multiple_comparison_label = "⚠️확인필요"

    treatments_out = []
    for (n, x), label in zip(treatments_raw, treatment_labels):
        stats = two_proportion_test(control_n, control_x, n, x)
        mde_met = compute_mde_met(stats["diff_ratio"], args.mde_abs, args.mde_rel, args.baseline)

        if args.bayes_method == "integrate":
            bayes = bayes_prob_treatment_better_integrate(control_n, control_x, n, x)
        else:
            bayes = bayes_prob_treatment_better_mc(
                control_n, control_x, n, x, seed=args.seed, draws=args.draws
            )

        if should_mask:
            verdict = "DESIGN_FAULT_SRM" if (srm_flag == "alarm" and mode == "verdict") else None
            entry = {
                "label": label,
                "n": n,
                "x": x,
                "rate": x / n,
                "diff_pp": None,
                "lift_rel_pct": None,
                "z": None,
                "p_two_sided": None,
                "statsig_pct": None,
                "ci95_lo_pp": None,
                "ci95_hi_pp": None,
                "bayes_p_treatment_better": None,
                "mde_met": None,
                "verdict": verdict,
            }
        else:
            verdict = determine_verdict(
                stats["statsig_pct"], stats["diff_pp"], mde_met, win_threshold_pct, STATSIG_CONTINUE_PCT
            )
            entry = {
                "label": label,
                "n": n,
                "x": x,
                "rate": x / n,
                "diff_pp": stats["diff_pp"],
                "lift_rel_pct": stats["lift_rel_pct"],
                "z": stats["z"],
                "p_two_sided": stats["p_two_sided"],
                "statsig_pct": stats["statsig_pct"],
                "ci95_lo_pp": stats["ci_lo_pp"],
                "ci95_hi_pp": stats["ci_hi_pp"],
                "bayes_p_treatment_better": bayes,
                "mde_met": mde_met,
                "verdict": verdict,
            }
            if needs_bonferroni_warning:
                entry["verdict"] = None
                entry["suppressed_reason"] = "multiple_comparison"
        treatments_out.append(entry)

    result = {
        "control": {"n": control_n, "x": control_x, "rate": control_x / control_n},
        "treatments": treatments_out,
        "srm": {
            "design_ratio": design_ratio,
            "observed_ratio": observed_ratio,
            "chi2": chi2,
            "p": srm_p,
            "flag": srm_flag,
        },
        "gate": {
            "gate_n": args.gate_n,
            "min_days": args.min_days,
            "days_elapsed": days_elapsed,
            "gate_reached": gate_reached,
            "mode": mode,
            "suppressed_reason": suppressed_reason,
        },
        "alpha": args.alpha,
        "alpha_effective": alpha_effective,
        "multiple_comparison": multiple_comparison_label,
        "seed": args.seed,
        "draws": args.draws,
        "bayes_method": args.bayes_method,
        "_force_applied": force_applied,
        "_control_label": args.label_control,
    }
    return result


# ---------------------------------------------------------------------------
# 출력 포맷
# ---------------------------------------------------------------------------


def format_json(result: dict) -> str:
    public = {k: v for k, v in result.items() if not k.startswith("_")}
    return json.dumps(public, ensure_ascii=False, indent=2)


def format_md(result: dict) -> str:
    lines = []
    if result.get("_force_applied"):
        lines.append("⚠️ 피킹 게이트 강제 해제 — 계약 §7-6 위반 기록")
        lines.append("")

    control = result["control"]
    control_label = result["_control_label"]
    lines.append("| 군 | 노출 | 전환 | 전환율 |")
    lines.append("|---|---|---|---|")
    lines.append(
        f"| {control_label} | {control['n']} | {control['x']} | {_fmt_ratio(control['rate'] * 100)}% |"
    )
    for t in result["treatments"]:
        lines.append(f"| {t['label']} | {t['n']} | {t['x']} | {_fmt_ratio(t['rate'] * 100)}% |")
    lines.append("")

    labels = [t["label"] for t in result["treatments"]]
    header = "| 항목 | " + " | ".join(labels) + " |"
    sep = "|---|" + "---|" * len(labels)
    lines.append(header)
    lines.append(sep)

    def row(name: str, values: list) -> str:
        return f"| {name} | " + " | ".join(values) + " |"

    srm = result["srm"]
    gate = result["gate"]

    diff_vals = [_fmt_ratio(t["diff_pp"]) for t in result["treatments"]]
    lift_vals = [_fmt_pct(t["lift_rel_pct"]) for t in result["treatments"]]
    z_vals = [_fmt_ratio(t["z"], 3) for t in result["treatments"]]
    p_vals = [_fmt_p(t["p_two_sided"]) for t in result["treatments"]]
    statsig_vals = [_fmt_pct(t["statsig_pct"]) for t in result["treatments"]]
    ci_vals = [
        "—" if t["ci95_lo_pp"] is None else f"[{_fmt_ratio(t['ci95_lo_pp'])}, {_fmt_ratio(t['ci95_hi_pp'])}]"
        for t in result["treatments"]
    ]
    bayes_vals = [
        "—" if t["bayes_p_treatment_better"] is None else f"{_fmt_ratio(t['bayes_p_treatment_better'] * 100)}%"
        for t in result["treatments"]
    ]
    mde_vals = [_fmt_bool(t["mde_met"]) for t in result["treatments"]]
    bonferroni_vals = [result["multiple_comparison"]] * len(labels)
    amplitude_vals = ["—"] * len(labels)
    srm_p_vals = [_fmt_p(srm["p"])] * len(labels)
    srm_flag_vals = [srm["flag"]] * len(labels)
    mode_vals = [gate["mode"]] * len(labels)
    verdict_vals = [_fmt_verdict(t["verdict"]) for t in result["treatments"]]

    lines.append(
        "<!-- 아래 10행 = 계약 M5b, 이어지는 4행 = M3b(SRM)·M4(모드)·M5c(판정)로 옮겨 적는다 -->"
    )
    lines.append(row("절대 차이(%p)", diff_vals))
    lines.append(row("상대 리프트", lift_vals))
    lines.append(row("z", z_vals))
    lines.append(row("p(양측)", p_vals))
    lines.append(row("stat-sig(1−p)", statsig_vals))
    lines.append(row("95% CI(미풀링)", ci_vals))
    lines.append(row("베이지안 P(실험군>대조군)", bayes_vals))
    lines.append(row("MDE 달성", mde_vals))
    lines.append(row("다중비교 보정", bonferroni_vals))
    lines.append(row("Amplitude 엔진 표시값(참고)", amplitude_vals))
    lines.append(row("SRM 카이제곱 p", srm_p_vals))
    lines.append(row("SRM 판정", srm_flag_vals))
    lines.append(row("모드", mode_vals))
    lines.append(row("판정", verdict_vals))

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------


def main() -> None:
    parser = build_arg_parser()
    args = parser.parse_args()

    result = build_result(args)

    if result.get("_force_applied"):
        print("⚠️ 피킹 게이트 강제 해제 — 계약 §7-6 위반 기록", file=sys.stderr)

    outputs = []
    if args.format in ("md", "both"):
        outputs.append(format_md(result))
    if args.format in ("json", "both"):
        outputs.append(format_json(result))
    print("\n\n".join(outputs))

    if args.out:
        try:
            with open(args.out, "w", encoding="utf-8") as f:
                f.write(format_json(result))
        except OSError as e:
            _fail(f"--out 파일을 쓸 수 없습니다: {args.out} ({e})")


if __name__ == "__main__":
    main()
