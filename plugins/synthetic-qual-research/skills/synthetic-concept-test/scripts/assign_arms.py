"""Generate the blind / order-assignment table (C4) for a synthetic concept
test (합성 UT) — ct-output-contract.md §3-5.

WHY THIS EXISTS: §7-5 makes order counterbalancing hard-mandatory — every
respondent must see the arms in a different order, and the order actually
shown must be written down before/at dispatch time, not reconstructed after
the fact. A plain "shuffle N times" can accidentally repeat the same order
for two respondents and nobody would notice. This script instead walks the
full list of possible permutations round-robin (a rotating Latin square) —
that guarantees no order repeats until every permutation has been used once,
which is what "counterbalancing" actually means (balance across possible
orders), not mere randomness. The random seed only picks *where in that
rotation* to start, so the result is fully reproducible: same --seed/--n/
--arms => byte-identical assignment.md and assignment.json.

It also runs the blind-vocabulary gate (§7-3) at label-definition time —
before any prompt is assembled — because a leaked "신규/기존" label makes
every downstream response worthless no matter how careful the rest of the
run is.

**단, 이 검사는 안 라벨(`--arms`)에만 적용된다 — §3-5 C4 4열·§7-3이 요구하는
「조립된 프롬프트 전문에 대한 검사」는 아니다.** 그 검사는 STEP 3(프롬프트
조립 시점)에서 일어나고 이 스크립트는 그 시점에 존재하지 않는다. 그래서
C4 4열·`assignment.json`의 `forbidden_check` 기본값은 "통과"가 아니라
"미검사 — 프롬프트 조립 시 기입"/`labels_only`다 — "통과"로 선기입하면
리뷰어가 보는 T-4(Critical) 근거가 자기증명이 되고, STEP 3 진입 조건("금지
어휘 검사가 통과다")이 스스로 충족되어 게이트가 사라진다. 프롬프트 조립을
실제로 하는 쪽(스킬)이 이 값을 STEP 3 결과로 덮어써야 한다.

Usage
-----
    python assign_arms.py --seed 42 --n 5 --arms "㉮,㉯,㉰" \
        --out /path/to/run/assignment.md [--uuids /path/to/drawn_personas.jsonl]

- `--arms`: comma-separated NEUTRAL symbols only (㉮㉯㉰㉱…). Labels like
  "기존안"/"신규안"/"A안"/"B안" are rejected — see FORBIDDEN_TERMS below.
- `--uuids`: optional drawn_personas.jsonl (see draw_personas.py). When given,
  each respondent row is labelled `RSP-{n} ({uuid8})`; otherwise `RSP-{n}`.
- Writes two files next to each other: `<out>` (C4 markdown table) and
  `<out-dir>/assignment.json` (machine-readable — aggregate_arms.py reads
  this to label respondents consistently).

주의
----
- 순열 수(2안=2, 3안=6, 4안=24…)보다 --n이 작으면 일부 순열이 아예 배정되지
  않는다 — 이는 균형이 깨진 것이므로 하드 에러가 아니라 **경고**로 stderr에
  낸다(빠진 순열 목록 포함). N을 순열 수 이상으로 늘리거나, 빠진 채로 갈지는
  참가자가 판단한다.
- 전역 `random` 모듈을 건드리지 않는다 — `random.Random(seed)` 인스턴스만
  쓴다. 다른 스크립트나 같은 세션의 다른 무작위 추출과 섞이면 재현성이
  깨진다.
"""
from __future__ import annotations
import argparse, itertools, json, os, random, sys

# §7-3 최소 검사 대상. 부분 문자열 매치이므로 "기존안"/"신규안"/"A안/B안" 등
# 계약 원문의 확장형도 함께 걸린다("기존" ⊂ "기존안" 등).
FORBIDDEN_TERMS = ["신규", "기존", "저희", "새로", "개선", "A안", "B안"]


def check_forbidden(arms: list[str]) -> list[str]:
    hits = []
    for arm in arms:
        for term in FORBIDDEN_TERMS:
            if term in arm:
                hits.append(f"{arm!r} 안에 금지어 {term!r}")
    return hits


def build_assignment(arms: list[str], n: int, seed: int):
    """Round-robin over all permutations of `arms`, starting point from seed.

    Returns (used_perms: list[tuple], num_perms, start_index, missing: list[tuple]).
    """
    perms = list(itertools.permutations(arms))
    num_perms = len(perms)

    rng = random.Random(seed)  # local instance — never touches the global random
    start = rng.randrange(num_perms)

    used_perms = [perms[(start + i) % num_perms] for i in range(n)]

    missing = []
    if n < num_perms:
        used_set = set(used_perms)
        missing = [p for p in perms if p not in used_set]

    return used_perms, num_perms, start, missing


def load_uuid8s(path: str, n: int) -> list[str]:
    uuid8s = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            row = json.loads(line)
            uuid8s.append(row["uuid"][:8])
    if len(uuid8s) < n:
        sys.exit(f"--uuids에 {len(uuid8s)}명뿐인데 --n={n}입니다. drawn_personas.jsonl을 확인하세요.")
    return uuid8s


def write_md(path, arms, seed, n, num_perms, start, missing, rows):
    lines = []
    lines.append("# C4. blind · 순서 배정 표")
    lines.append("")
    lines.append(f"- 안: {', '.join(arms)}")
    lines.append(f"- 시드: {seed}")
    lines.append(f"- 순열 수: {num_perms} (시작 인덱스 {start})")
    lines.append("")
    lines.append("| 응답자 | 제시 순서 | counterbalancing 방식 | 금지 어휘 검사 |")
    lines.append("|---|---|---|---|")
    for respondent, order_str, cb_note, forbidden_result in rows:
        lines.append(f"| {respondent} | {order_str} | {cb_note} | {forbidden_result} |")
    if missing:
        missing_str = ", ".join(" → ".join(p) for p in missing)
        lines.append("")
        lines.append(f"⚠️ 배정되지 않은 순열 {len(missing)}개 — 균형이 깨졌습니다 (§7-5): {missing_str}")
    lines.append("")
    with open(path, "w") as f:
        f.write("\n".join(lines))


def write_json(path, seed, n, arms, num_perms, start, missing, assignments, forbidden_check):
    payload = {
        "seed": seed,
        "n": n,
        "arms": arms,
        "num_permutations": num_perms,
        "start_index": start,
        "missing_permutations": [list(p) for p in missing],
        "forbidden_check": forbidden_check,
        "assignments": assignments,
    }
    with open(path, "w") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
        f.write("\n")


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--seed", type=int, required=True)
    ap.add_argument("--n", type=int, required=True)
    ap.add_argument("--arms", required=True, help='쉼표 구분 중립 기호, 예: "㉮,㉯,㉰"')
    ap.add_argument("--out", required=True, help="assignment.md 출력 경로")
    ap.add_argument("--uuids", help="drawn_personas.jsonl 경로 (있으면 uuid8 병기)")
    args = ap.parse_args()

    arms = [a.strip() for a in args.arms.split(",") if a.strip()]
    if len(arms) < 2:
        sys.exit("안은 최소 2개 이상이어야 합니다 (§7-2 대조군 arm 필수 — 시안 단독 제시 금지).")

    hits = check_forbidden(arms)
    if hits:
        sys.exit(
            "금지 어휘 발견 — 계약 §7-3(blind 유지): 어느 쪽이 신규 시안인지 드러내는 표현을 "
            "쓰면 안 됩니다. 라벨은 중립 기호(㉮㉯㉰㉱…)만 허용합니다.\n" + "\n".join(hits)
        )

    if args.n < 1:
        sys.exit("--n은 1 이상이어야 합니다.")

    used_perms, num_perms, start, missing = build_assignment(arms, args.n, args.seed)

    uuid8s = load_uuid8s(args.uuids, args.n) if args.uuids else None

    rows = []
    assignments = []
    for i in range(args.n):
        order = used_perms[i]
        label = f"RSP-{i + 1}"
        respondent = f"{label} ({uuid8s[i]})" if uuid8s else label
        order_str = " → ".join(order)
        cb_note = f"순환(라틴방격) — 순열 {num_perms}개 중 시작 인덱스 {start} (seed={args.seed})"
        rows.append((respondent, order_str, cb_note, "미검사 — 프롬프트 조립 시 기입"))
        assignments.append({
            "respondent": label,
            "uuid8": uuid8s[i] if uuid8s else None,
            "order": list(order),
        })

    write_md(args.out, arms, args.seed, args.n, num_perms, start, missing, rows)

    json_path = os.path.join(os.path.dirname(os.path.abspath(args.out)), "assignment.json")
    write_json(json_path, args.seed, args.n, arms, num_perms, start, missing, assignments, "labels_only")

    print(f"wrote {args.n} respondent(s) -> {args.out}", file=sys.stderr)
    print(f"wrote machine-readable assignment -> {json_path}", file=sys.stderr)
    if missing:
        missing_str = ", ".join(" → ".join(p) for p in missing)
        print(
            f"WARNING: 순열 {num_perms}개 중 {len(missing)}개가 배정되지 않았습니다 "
            f"— 균형이 깨졌습니다 (§7-5): {missing_str}",
            file=sys.stderr,
        )


if __name__ == "__main__":
    main()
