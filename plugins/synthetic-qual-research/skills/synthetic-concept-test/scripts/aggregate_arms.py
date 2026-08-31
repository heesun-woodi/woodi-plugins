"""Aggregate C5 (respondent × axis responses) into C6 (per-arm n/N table)
for a synthetic concept test (합성 UT) — ct-output-contract.md §3-6 · §3-7.

WHY THIS EXISTS: §7-9 forbids folding the three axes (멈춤/믿음/실행의향)
into one score, and §7-10 caps what any output here is allowed to say about
the arms — a fact ("사전등록 채택조건 충족") is fine, a verdict ("㉯ 채택")
is not. Both rules are easy to violate by accident while writing prose, so
this script enforces them mechanically: it never sums/averages the three
axes, and it scans its own finished output for verdict-shaped language
before writing anything to disk.

**Self-scan은 스킬이 생성한 문장만 검사한다.** 참가자가 prereg.md에 스스로
써 둔 채택/기각 조건 원문은 §3-2(C1) 규칙을 지킨 정상 문장이라도 "㉯를
채택한다"처럼 '채택'이라는 단어를 합법적으로 담을 수 있다 — 이건 사실
인용이지 이 스크립트의 판정 선언이 아니다. 그래서 원문 인용은 항상 `> `로
시작하는 블록쿼트 줄로만 내보내고(`render_markdown`의 「사전등록 조건 원문」
절), self_scan은 그 줄들을 통째로 스캔 대상에서 뺀다 — "단어가 있으면
인용일 것"이라는 추측이 아니라 "블록쿼트 줄이면 인용"이라는 기계적 규칙이다.
스킬이 직접 만드는 문장(C6 표 셀 등)은 여전히 전체 강도로 스캔한다.

results.json schema (this script's own contract — folds the C5 columns into
JSON; §3-6 is the source of truth for what each field means):
    {
      "<uuid>": {
        "arms": {
          "<안 기호, 예: ㉮>": {
            "stop":        "멈춤" | "안 멈춤" | "애매함",
            "stop_note":   "<한 줄 근거>",           (선택)
            "belief":      "믿음" | "안 믿음" | "애매함",
            "belief_note": "<한 줄 근거>",           (선택)
            "intent":      "넘긴다" | "본다" | "눌러본다",
            "quote":       "<응답자 원문 — 요약·윤문 금지>"
          }, ...
        },
        "counterfactual": "<반사실 답변 원문>"        (없으면 "미확보"로 간주)
      }, ...
    }
`arms`가 없거나, 개별 안 응답에 stop/belief/intent/quote 중 하나라도 없거나
값이 도메인 밖이면 그 (uuid, 안) 슬롯은 SCHEMA VIOLATION — 집계에서 제외하고
재디스패치 목록으로 보고한다(exit 3). validate_results.py가 이미 통과했다는
전제이므로 UUID 자체의 존재 여부는 여기서 다시 검사하지 않는다.

Usage
-----
    # 집계 모드 (C5 -> C6)
    python aggregate_arms.py --results /run/results.json --prereg /run/prereg.md \
        [--assignment /run/assignment.json] --out /run/aggregate.md

    # --text 단독 모드 — 집계 없이, 이미 조립된 텍스트(예: 스킬이 직접 쓴
    # C8a 노션 갱신 블록)에 §7-10 self-scan만 돌린다. aggregate.md는 이
    # 스크립트가 생성해 self_scan을 거치지만, C8a는 상류 재료(집계 결과)를
    # 스킬이 조립하는 별도 산출물이라 같은 검사를 한 번 더 받아야
    # 비대칭이 없다(critic C-7 조건). --results와 동시에 줄 수 없다.
    python aggregate_arms.py --text /run/c8a_block.md

주의 — 이 계약 해석이 갈리는 지점 (완료 보고 참고)
----
- **n/N 분자 정의 (확정)**: 멈춤=`멈춤` 개수, 믿음=`믿음` 개수,
  실행의향=`눌러본다` 개수를 분자로 쓴다. 세 축 모두 **괄호 안에 3값 분포를
  전부 병기**한다 — 예: `2/5 (눌러본다 2 · 본다 1 · 넘긴다 2)`. 실행의향만
  분포를 병기하면 표기가 축마다 달라져 리뷰어가 헷갈리므로, 멈춤·믿음도
  같은 방식으로 통일했다(§3-7의 「백분율 단독 표기 금지」는 분포 표기에도
  그대로 적용 — 전부 개수다). 다르게 셀 근거가 있으면 `count_axis`/
  `format_axis`만 바꾸면 된다.
- **C1 조건 대조**: prereg.md의 채택/기각 조건은 자연어 문장이라, 이 스크립트가
  그 의미를 함부로 해석하면 §7-10을 코드로 위반하는 셈이다. 그래서 조건
  문장에 "N명 중 n명 이상" + 안 기호 + 축 키워드가 **명시적으로** 다 들어있는
  경우에만 기계적으로 대조하고, 그 외에는 전부 `조건 밖 — 대조 불가`로
  남긴다. 이 판정은 최종 채택·기각 선언이 아니라 사실 대조일 뿐이며,
  최종 판단은 ed 세션에서 사람이 한다(§0-2).
"""
from __future__ import annotations
import argparse, json, re, sys
from collections import Counter

STOP_VALUES = {"멈춤", "안 멈춤", "애매함"}
BELIEF_VALUES = {"믿음", "안 믿음", "애매함"}
INTENT_VALUES = {"넘긴다", "본다", "눌러본다"}
REQUIRED_ARM_KEYS = ["stop", "belief", "intent", "quote"]

# 분자(첫 값) 순서로 나열 — format_axis가 "n/N (첫값 a · 둘째 b · 셋째 c)" 순으로 쓴다.
STOP_ORDER = ["멈춤", "안 멈춤", "애매함"]
BELIEF_ORDER = ["믿음", "안 믿음", "애매함"]
INTENT_ORDER = ["눌러본다", "본다", "넘긴다"]

# §7-10 판정권 상한 자기검사 — 이 문자열들은 "사실 진술"이라 허용한다.
# "채택"/"기각"이 이 문구들 밖에서 등장하면 단독 선언(㉯ 채택 등)일 가능성이
# 높으므로 걸러낸다. 화이트리스트 방식을 쓰는 이유는 계약 §7-10·§3-7이
# 명시한 것처럼 "사전등록 채택조건 충족"은 사실 진술이고, 이를 "㉯ 채택"으로
# 번역하는 순간 위반이 되기 때문 — 번역(의미 변환)은 사람이 한다.
WHITELIST_PHRASES = [
    "사전등록 채택조건 충족",
    "사전등록 기각조건 충족",
    "조건 밖 — 대조 불가",
    "채택 조건",  # C1 행 이름을 그대로 인용할 때 쓰는 라벨
    "기각 조건",  # C1 행 이름을 그대로 인용할 때 쓰는 라벨
]
FORBIDDEN_TOKENS = ["채택", "기각", "순위", "탈락", "1순위", "추천", "권장"]

WARNING_BANNER = (
    "⚠️ 아래는 합성 인터뷰 결과로, 가설이지 근거가 아닙니다. 실제 고객 UT·"
    "상담사 인터뷰로 검증 전까지 확정된 문제로 취급하지 마세요."
)


def load_results(path):
    with open(path) as f:
        data = json.load(f)
    if not isinstance(data, dict):
        sys.exit(f"입력 오류: {path}는 최상위가 객체({{uuid: {{...}}}})여야 합니다.")
    return data


def validate_slot(uuid, arm, resp):
    """Return (ok, reason). ok=False -> exclude from aggregation, report."""
    if not isinstance(resp, dict):
        return False, "응답이 객체가 아님"
    missing = [k for k in REQUIRED_ARM_KEYS if k not in resp or resp[k] in (None, "", [], {})]
    if missing:
        return False, f"필수 키 누락/공백: {missing}"
    if resp["stop"] not in STOP_VALUES:
        return False, f"stop 값이 도메인 밖: {resp['stop']!r}"
    if resp["belief"] not in BELIEF_VALUES:
        return False, f"belief 값이 도메인 밖: {resp['belief']!r}"
    if resp["intent"] not in INTENT_VALUES:
        return False, f"intent 값이 도메인 밖: {resp['intent']!r}"
    return True, ""


def collect_slots(results):
    """Walk results.json -> (valid_slots, invalid_slots, counterfactuals).

    valid_slots: dict[(uuid, arm)] -> response dict
    invalid_slots: list[(uuid, arm_or_None, reason)]
    counterfactuals: dict[uuid] -> text (respondents with no 'arms' at all are
      still recorded here if they at least carry a counterfactual, since that
      question is asked independently of per-arm responses per §7-7).
    """
    valid_slots, invalid_slots, counterfactuals = {}, [], {}
    for uuid, record in results.items():
        if not isinstance(record, dict) or not isinstance(record.get("arms"), dict) or not record.get("arms"):
            invalid_slots.append((uuid, None, "'arms' 없음/빈 값 — 응답자 전체 슬롯 재디스패치 필요"))
        else:
            for arm, resp in record["arms"].items():
                ok, reason = validate_slot(uuid, arm, resp)
                if ok:
                    valid_slots[(uuid, arm)] = resp
                else:
                    invalid_slots.append((uuid, arm, reason))
        cf = record.get("counterfactual") if isinstance(record, dict) else None
        counterfactuals[uuid] = cf if cf else "미확보"
    return valid_slots, invalid_slots, counterfactuals


def count_axis(valid_slots, arm):
    """N + per-value Counter for each axis, one arm. See module docstring
    '주의' for the numerator/분포 표기 정의."""
    slots = [resp for (u, a), resp in valid_slots.items() if a == arm]
    N = len(slots)
    stop_dist = Counter(r["stop"] for r in slots)
    belief_dist = Counter(r["belief"] for r in slots)
    intent_dist = Counter(r["intent"] for r in slots)
    return N, stop_dist, belief_dist, intent_dist


def format_axis(dist, order, N):
    """'n/N (첫값 a · 둘째 b · 셋째 c)' — n은 order[0]의 개수. 전부 정수
    개수이고 백분율은 어디에도 안 쓴다(§3-7)."""
    n = dist.get(order[0], 0)
    breakdown = " · ".join(f"{value} {dist.get(value, 0)}" for value in order)
    return n, f"{n}/{N} ({breakdown})"


def parse_prereg(path):
    """Best-effort extraction of the 채택 조건 / 기각 조건 rows from prereg.md.

    prereg.md is C1 — a 2-column (항목/값) markdown table per §3-2. This
    parser handles both a markdown table row (`| 채택 조건 | ... |`) and a
    plain `label: value` line, and returns the value text verbatim (quoted,
    never paraphrased) so the C6 cell can cite it directly.
    """
    labels = {"채택 조건": None, "기각 조건": None}
    with open(path, encoding="utf-8") as f:
        text = f.read()
    for line in text.splitlines():
        stripped = line.strip()
        for label in labels:
            if label not in stripped:
                continue
            if stripped.startswith("|"):
                cells = [c.strip().strip("*") for c in stripped.strip("|").split("|")]
                if len(cells) >= 2 and label in cells[0]:
                    labels[label] = cells[1]
            else:
                m = re.search(rf"{re.escape(label)}\s*[:：]\s*(.+)", stripped)
                if m:
                    labels[label] = m.group(1).strip().strip("*")
    return labels


# "N명 중 n명 이상" + 안 기호 + 축 키워드가 모두 명시된 경우에만 기계적으로
# 대조한다. 그 외 자연어는 해석하지 않고 '조건 밖 — 대조 불가'로 남긴다.
THRESHOLD_RE = re.compile(r"(\d+)\s*명\s*중\s*(\d+)\s*명\s*이상")
# 분자는 각 축의 긍정값 하나뿐이다(멈춤=`멈춤`, 믿음=`믿음`, 실행의향=`눌러본다`
# — count_axis/AXIS_ORDER와 동일). 키워드도 그 값 자체로 찾는다.
AXIS_KEYWORDS = {
    "멈춤": ["멈춤"],
    "믿음": ["믿음"],
    "실행의향": ["눌러본다"],
}
# "안 멈춤"/"안 믿음"은 "멈춤"/"믿음"의 부분 문자열이다 — 그대로 키워드
# 매칭을 돌리면 부정형 조건("㉯에서 안 멈춤")이 긍정 축("멈춤")으로 오매치되고,
# 분자는 여전히 `멈춤` 개수라 반대 판정("사전등록 채택조건 충족")이 나온다
# (리뷰 C-6). 그래서 매칭 전에 이 부정형 구절부터 지운다 — 지우고 나면
# "멈춤"/"믿음"이 조건문에 안 남으므로 그런 조건은 자동으로 '조건 밖 —
# 대조 불가'로 떨어진다. 부정형 조건까지 자동 대조하고 싶으면 여기 로직을
# 확장해야 하고, 지금은 (기존 설계 철학대로) 안전한 쪽으로 보수적으로 둔다.
NEGATIVE_PHRASES_TO_STRIP = ["안 멈춤", "안 믿음"]


def evaluate_condition(condition_text, arm, N, n_stop, n_belief, n_intent):
    """Mechanical, conservative check — see module docstring. Never guesses.

    Returns (result: bool|None, axis_label: str|None, n_used: int|None,
    n_required: int|None). result is None whenever the condition text can't
    be matched unambiguously — the caller must then fall back to '조건 밖'."""
    if not condition_text or arm not in condition_text:
        return None, None, None, None
    m = THRESHOLD_RE.search(condition_text)
    if not m:
        return None, None, None, None
    n_required = int(m.group(2))
    axis_counts = {"멈춤": n_stop, "믿음": n_belief, "실행의향": n_intent}
    scrubbed = condition_text
    for neg in NEGATIVE_PHRASES_TO_STRIP:
        scrubbed = scrubbed.replace(neg, "")
    for axis, keywords in AXIS_KEYWORDS.items():
        if any(kw in scrubbed for kw in keywords):
            return axis_counts[axis] >= n_required, axis, axis_counts[axis], n_required
    return None, None, None, None


def build_c6(arms, valid_slots, prereg):
    rows = []
    for arm in arms:
        N, stop_dist, belief_dist, intent_dist = count_axis(valid_slots, arm)
        n_stop, stop_cell = format_axis(stop_dist, STOP_ORDER, N)
        n_belief, belief_cell = format_axis(belief_dist, BELIEF_ORDER, N)
        n_intent, intent_cell = format_axis(intent_dist, INTENT_ORDER, N)

        adopt_ok, adopt_axis, adopt_n, adopt_req = evaluate_condition(
            prereg.get("채택 조건"), arm, N, n_stop, n_belief, n_intent
        )
        reject_ok, reject_axis, reject_n, reject_req = evaluate_condition(
            prereg.get("기각 조건"), arm, N, n_stop, n_belief, n_intent
        )
        # 조건 원문은 여기서 인용하지 않는다 — 원문 인용은 render_markdown의
        # 블록쿼트 절에서만 하고(그래야 self_scan이 그 줄만 빼고 스캔할 수
        # 있다), 이 셀은 스킬이 만든 수치 문장만 담는다.
        if adopt_ok is True:
            verdict = (
                f"사전등록 채택조건 충족 — {adopt_axis} {adopt_n}/{N} "
                f"(기준 {adopt_req}명 이상, 채택 조건 원문은 아래 참고)"
            )
        elif reject_ok is True:
            verdict = (
                f"사전등록 기각조건 충족 — {reject_axis} {reject_n}/{N} "
                f"(기준 {reject_req}명 이상, 기각 조건 원문은 아래 참고)"
            )
        else:
            verdict = "조건 밖 — 대조 불가"
        rows.append((arm, N, stop_cell, belief_cell, intent_cell, verdict))
    return rows


def find_cross_votes(arms, valid_slots):
    """Respondents whose 'positive' arm differs across axes (§7-9 실측 사례:
    '믿음은 A안, 팔로우는 C안'). Purely descriptive — no ranking of arms.

    '긍정값'은 build_c6/count_axis의 분자 정의와 반드시 같아야 한다 —
    멈춤=`멈춤`, 믿음=`믿음`, 실행의향=`눌러본다`. 한 파일 안에서 축 정의가
    갈리면(예: 여기서만 `안 멈춤`을 긍정으로 잡으면) 같은 데이터를 보고
    C6과 교차 투표 절이 서로 다른 이야기를 하게 된다 (리뷰 C-6/C-2)."""
    by_uuid = {}
    for (uuid, arm), resp in valid_slots.items():
        by_uuid.setdefault(uuid, {})[arm] = resp

    cross_votes = []
    for uuid, arm_resps in by_uuid.items():
        if len(arm_resps) < 2:
            continue
        stop_positive = sorted(a for a, r in arm_resps.items() if r["stop"] == "멈춤")
        belief_positive = sorted(a for a, r in arm_resps.items() if r["belief"] == "믿음")
        intent_positive = sorted(a for a, r in arm_resps.items() if r["intent"] == "눌러본다")
        axis_sets = {"멈춤": set(stop_positive), "믿음": set(belief_positive), "실행의향": set(intent_positive)}
        nonempty = {k: v for k, v in axis_sets.items() if v}
        distinct_sets = {frozenset(v) for v in nonempty.values()}
        if len(distinct_sets) > 1:
            cross_votes.append((uuid, nonempty))
    return cross_votes


def render_markdown(arms, c6_rows, cross_votes, invalid_slots, prereg, respondent_labels):
    lines = [WARNING_BANNER, "", "## C6. 집계 표", ""]
    lines.append("| 안 | 멈춤 | 믿음 | 실행의향 | C1 조건 대조 |")
    lines.append("|---|---|---|---|---|")
    for arm, N, stop_cell, belief_cell, intent_cell, verdict in c6_rows:
        lines.append(f"| {arm} | {stop_cell} | {belief_cell} | {intent_cell} | {verdict} |")

    lines += ["", "## 교차 투표 (응답자별 축 분리)", ""]
    if cross_votes:
        lines.append("| 응답자 | 멈춤 긍정 안 | 믿음 긍정 안 | 실행의향(눌러본다) 긍정 안 |")
        lines.append("|---|---|---|---|")
        for uuid, axis_sets in cross_votes:
            label = respondent_labels.get(uuid, uuid[:8])
            stop_v = ", ".join(sorted(axis_sets.get("멈춤", []))) or "—"
            belief_v = ", ".join(sorted(axis_sets.get("믿음", []))) or "—"
            intent_v = ", ".join(sorted(axis_sets.get("실행의향", []))) or "—"
            lines.append(f"| {label} | {stop_v} | {belief_v} | {intent_v} |")
    else:
        lines.append("(교차 투표 없음 — 축별 긍정 안이 동일하거나 판단 불가)")

    lines += ["", "## 스키마 위반 슬롯 (재디스패치 필요)", ""]
    if invalid_slots:
        lines.append("| 응답자 | 안 | 사유 |")
        lines.append("|---|---|---|")
        for uuid, arm, reason in invalid_slots:
            label = respondent_labels.get(uuid, uuid[:8])
            lines.append(f"| {label} | {arm or '(전체)'} | {reason} |")
    else:
        lines.append("(없음)")

    lines += ["", "## 사전등록 조건 원문 (참가자 작성 — 원문 인용)", ""]
    for label in ("채택 조건", "기각 조건"):
        value = prereg.get(label)
        if value:
            # 참가자가 스스로 쓴 원문 — 블록쿼트(`> `)로만 낸다. self_scan은
            # 이 접두사가 붙은 줄을 통째로 검사 대상에서 뺀다.
            lines.append(f"> {label}: {value} _(참가자 원문 인용 — §7-10 검사 대상 아님)_")
        else:
            lines.append(f"⚠️ {label}: prereg.md에서 파싱 실패")
    lines.append("")

    assert_quote_invariant(lines)
    return "\n".join(lines)


QUOTE_SECTION_HEADING = "## 사전등록 조건 원문"


def assert_quote_invariant(lines):
    """Lock the invariant self_scan() relies on: `> `-prefixed lines may only
    appear inside the 「사전등록 조건 원문」 절. self_scan() exempts every such
    line from the §7-10 self-check — that's correct only because today's only
    producer of '> ' lines is the prereg-quote loop right above. If a future
    edit adds another blockquote-emitting section (e.g. quoting C7 걸림돌
    원문), the exemption would silently widen to cover it too, with nothing
    to catch it in review. This assertion is that catch — it fails loudly at
    generation time instead of quietly widening the exemption."""
    try:
        quote_section_start = next(i for i, l in enumerate(lines) if l.startswith(QUOTE_SECTION_HEADING))
    except StopIteration:
        quote_section_start = len(lines)  # section itself missing -> any '>' line anywhere is a violation
    stray = [(i, l) for i, l in enumerate(lines) if i < quote_section_start and l.lstrip().startswith(">")]
    if stray:
        detail = "; ".join(f"줄 {i}: {l!r}" for i, l in stray)
        raise AssertionError(
            f"'> ' 블록쿼트 불변식 위반 — 「{QUOTE_SECTION_HEADING}」 절 밖에서 블록쿼트가 나왔습니다 "
            f"({detail}). self_scan()이 이 줄들까지 §7-10 검사 대상에서 빼게 되므로 판정권 상한 "
            "검사가 무력화됩니다. 새 절에서 원문을 인용하려면 그 절도 「사전등록 조건 원문」 절 "
            "안으로 옮기거나, self_scan()의 예외 규칙을 그 절까지 명시적으로 넓히고 여기 검사도 "
            "함께 갱신하세요."
        )


def scan_violations(text):
    """Line-level §7-10 self-check — the ONE place the blockquote-exemption
    and whitelist rule live. self_scan() (used by the aggregate pipeline) and
    the --text standalone mode (used to check an already-assembled C8a block
    the skill wrote by hand) both call this, so the rule can't drift between
    the two call sites.

    Lines starting with '> ' are participant-authored quotes (prereg 원문 in
    this script's own output, or — per §3-9's citation format — a quoted
    passage anywhere else, e.g. C8a) and are skipped wholesale: a
    legitimately-written "㉯를 채택한다" inside a participant's own C1 조건
    문장 is a fact to cite, not a verdict this script/skill is issuing. The
    rule is a mechanical line-prefix check, not a guess based on which words
    appear, and it doesn't care about the exact wording after '> ' — §3-9's
    `> 채택 조건(사전등록 원문, 인용):` format is covered the same as this
    script's own `> 채택 조건: ...` format.

    On every other line, forbidden tokens are checked after whitelisted
    fact-statement phrases are stripped out — see module docstring for why a
    whitelist (not a blanket ban) is required.

    Returns list of (line_no, line_text, tokens_found) for 1-indexed lines
    that still contain a forbidden token after scrubbing."""
    violations = []
    for i, line in enumerate(text.splitlines(), start=1):
        if line.lstrip().startswith(">"):
            continue
        scrubbed = line
        for phrase in WHITELIST_PHRASES:
            scrubbed = scrubbed.replace(phrase, "")
        found = [tok for tok in FORBIDDEN_TOKENS if tok in scrubbed]
        if found:
            violations.append((i, line, found))
    return violations


def self_scan(text):
    """§7-10 판정권 상한 self-check over sentences THIS SCRIPT generated —
    see scan_violations() for the actual rule. Returns the flat, deduped list
    of forbidden tokens found anywhere (order follows FORBIDDEN_TOKENS), which
    is what the aggregate pipeline's error message uses."""
    found_tokens = {tok for _, _, toks in scan_violations(text) for tok in toks}
    return [tok for tok in FORBIDDEN_TOKENS if tok in found_tokens]


def load_respondent_labels(assignment_path):
    """uuid8 -> 'RSP-n (uuid8)' from assign_arms.py's assignment.json, keyed
    loosely since results.json is keyed by full uuid, not uuid8."""
    if not assignment_path:
        return {}
    with open(assignment_path) as f:
        payload = json.load(f)
    labels = {}
    for a in payload.get("assignments", []):
        if a.get("uuid8"):
            labels[a["uuid8"]] = f"{a['respondent']} ({a['uuid8']})"
    return labels


def resolve_labels(counterfactuals, uuid8_labels):
    labels = {}
    for uuid in counterfactuals:
        labels[uuid] = uuid8_labels.get(uuid[:8], uuid[:8])
    return labels


def run_text_scan(path):
    """Standalone §7-10 self-check over an already-assembled block of text —
    e.g. the C8a 노션 갱신 블록, which the skill assembles itself rather than
    this script generating it. Reuses scan_violations() so the rule (blockquote
    exemption + whitelist) can't diverge from the aggregate pipeline's."""
    try:
        with open(path, encoding="utf-8") as f:
            text = f.read()
    except FileNotFoundError as e:
        sys.exit(f"입력 오류: {e}")

    violations = scan_violations(text)
    if violations:
        print(
            f"판정권 상한(§7-10) 위반 — {path}의 {len(violations)}줄에서 금지 어휘가 발견되어 "
            "착지시키지 않습니다:",
            file=sys.stderr,
        )
        for line_no, line_text, tokens in violations:
            print(f"  줄 {line_no} {tokens}: {line_text.strip()}", file=sys.stderr)
        print("위 줄을 고치거나(허용된 사실 진술 문구로), 참가자 원문 인용이면 '> '로 감싸세요.", file=sys.stderr)
        sys.exit(1)

    print(f"판정권 상한(§7-10) 검사 통과 — {path}에 금지 어휘가 없습니다(인용 절 제외).", file=sys.stderr)
    sys.exit(0)


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--results", help="results.json (집계 모드 필수)")
    ap.add_argument("--prereg", help="prereg.md (집계 모드 필수)")
    ap.add_argument("--assignment", help="assign_arms.py가 낸 assignment.json (선택)")
    ap.add_argument("--out", help="aggregate.md 출력 경로 (집계 모드 필수)")
    ap.add_argument(
        "--text",
        help="집계하지 않고, 이 파일(예: 조립된 C8a 블록)에 §7-10 self-scan만 돌린다. "
             "--results와 동시에 줄 수 없다.",
    )
    args = ap.parse_args()

    if args.text and args.results:
        sys.exit(
            "--text와 --results를 동시에 줄 수 없습니다 — 모드를 하나만 고르세요: "
            "--text는 이미 조립된 텍스트(예: C8a)에 판정권 self-scan만 돌리고, "
            "기본 모드는 --results/--prereg로 C6을 집계합니다."
        )

    if args.text:
        run_text_scan(args.text)
        return  # run_text_scan always sys.exit()s; return is unreachable but explicit

    missing = [name for name, val in (("--results", args.results), ("--prereg", args.prereg), ("--out", args.out)) if not val]
    if missing:
        sys.exit(f"집계 모드에는 {', '.join(missing)}가 필요합니다 (또는 --text 단독 모드를 쓰세요).")

    try:
        results = load_results(args.results)
        prereg = parse_prereg(args.prereg)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        sys.exit(f"입력 오류: {e}")

    valid_slots, invalid_slots, counterfactuals = collect_slots(results)
    if not valid_slots:
        sys.exit("입력 오류: results.json에 유효한 (uuid, 안) 슬롯이 하나도 없습니다.")

    arms = sorted({a for (_, a) in valid_slots.keys()})
    c6_rows = build_c6(arms, valid_slots, prereg)
    cross_votes = find_cross_votes(arms, valid_slots)

    uuid8_labels = {}
    try:
        uuid8_labels = load_respondent_labels(args.assignment)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"경고: --assignment 로드 실패({e}) — uuid8 라벨 없이 진행합니다.", file=sys.stderr)

    respondent_labels = resolve_labels(counterfactuals, uuid8_labels)

    try:
        markdown = render_markdown(arms, c6_rows, cross_votes, invalid_slots, prereg, respondent_labels)
    except AssertionError as e:
        sys.exit(f"내부 불변식 위반 — 착지시키지 않습니다: {e}")

    violations = self_scan(markdown)
    if violations:
        print(
            "판정권 상한(§7-10) 위반 — 아래 어휘가 사실 진술 화이트리스트 밖에서 발견되어 "
            f"착지시키지 않습니다: {violations}",
            file=sys.stderr,
        )
        print("aggregate.md를 쓰지 않았습니다. 위 어휘가 나온 대목을 고치고 다시 실행하세요.", file=sys.stderr)
        sys.exit(1)

    with open(args.out, "w") as f:
        f.write(markdown)

    print(f"wrote C6 aggregate -> {args.out}", file=sys.stderr)
    print(f"arms={arms}  valid_slots={len(valid_slots)}  invalid_slots={len(invalid_slots)}  "
          f"cross_votes={len(cross_votes)}", file=sys.stderr)

    if invalid_slots:
        print(f"\n{len(invalid_slots)} slot(s) 스키마 위반 — 재디스패치 필요:", file=sys.stderr)
        for uuid, arm, reason in invalid_slots:
            print(f"  {uuid[:8]} / {arm or '(전체)'} — {reason}", file=sys.stderr)
        sys.exit(3)

    sys.exit(0)


if __name__ == "__main__":
    main()
