# Survey output skeleton

Use this as the shape of the deliverable. Keep the `ⓘ` designer notes inline — they explain why
each item is shaped as it is, which makes the survey teachable and defensible. Replace bracketed
placeholders. Every substantive item carries an `→RQ#` tag.

---

## 0. Backward-design matrix (show FIRST)

**Goal chain**
```
[Goal]      [the decision/action]
[Evidence]  [what data settles it]
[Knowledge] [what must be learned]
[Survey]    [the survey's one-line job]
```

| # | Research Question | Evidence needed | Question areas |
|---|---|---|---|
| RQ1 | … | … | … |
| RQ2 | … | … | … |
| RQ3 | … | … | … |
| RQ4 | … | … | … |

---

## 📋 [Survey title — respondent-facing, benefit-framed]

**대상**: [audience / persona filter] · **소요**: 약 [n]분 · **문항**: [n]개

> **도입 문구**: [1–2 sentences that lower the guard — "정답 없음", short, why it helps.]

### A. 스크리닝 & 기본 정보  `→세그먼트/필터`
- **A1.** [age/life-stage] — ☐ … ☐ …
- **A2.** [current situation] — ☐ … ☐ …
- **A3.** [segmenting var used later in cross-tabs] — ☐ … ☐ …
> ⓘ These double as the persona filter for nemotron dispatch. Capture in filterable terms.

### B. [Motivation / appeal section]  `→RQ1`
- **B1. (Likert battery)** [stem]. (1 전혀 그렇지 않다 … 5 매우 그렇다)

  | 항목 | 1 | 2 | 3 | 4 | 5 |
  |---|---|---|---|---|---|
  | [positively-keyed item] | ☐ | ☐ | ☐ | ☐ | ☐ |
  | [item — embed the ones your offer is strong at, mixed in] | ☐ | ☐ | ☐ | ☐ | ☐ |
  > ⓘ Explicit symmetric anchors; embed strength-relevant items among neutral ones to measure the appeal∩strength overlap.

- **B2. (forced rank / single)** [pick the one that matters most] → ______  `→RQ1`
- **B3. (open, unaided)** [ideal-scenario / first-association, placed BEFORE any option list]  `→RQ1`
  > ⓘ Raw language before priming = copy source. Texture, not counts.

### C. [Perception / concern section]  `→RQ2 / RQ3`
- **C1. (open)** [first word/image association] `→RQ2`
- **C2. (Likert battery, balanced keying)** [mix 1 positive + several concern/barrier items] `→RQ3`
  > ⓘ Negatively-keyed items counter acquiescence; quantifies what to pre-empt.

### D. [Barriers section]  `→RQ3`  ⭐ decision-critical
- **D1. (single choice)** [biggest single blocker] — ☐ … ☐ … ☐ 딱히 없다
- **D2. (open)** [what would reassure you] `→RQ3`
  > ⓘ Becomes the FAQ / message the offer must answer.

### E. [Intent / commitment section]  `→RQ4`  ⭐ goal-linked (for conversion goals)
- **E1. (intent scale)** [would you take the action?] (1 전혀 … 5 꼭)
- **E2. (single)** [what would make you act] `→RQ4`
- **E3. (open)** [what you'd most want to know before acting] `→RQ4`
- **E4. (commitment, loss-framed, soft middle option)**  `→goal`
  - ☐ 네 → [minimal capture]  ☐ 아직 고민 중 — 정보만  ☐ 지금은 괜찮아요
  > ⓘ Loss framing + soft middle keeps hesitant respondents as leads. Synthetic: read as relative, not literal rate.

---

## Analysis-to-decision plan (show AFTER the survey)

**Analysis plan**

| RQ | Load-bearing item | Explaining item | Move |
|---|---|---|---|
| … | … | … | … |

**Decision bridge**

| Finding | Action |
|---|---|
| … | … |

*(For message/offer goals, add a finding → strength → copy-hook table; mark any strength you had to assume.)*

---

> **Handoff**: To collect responses from synthetic Korean personas, run
> `nemotron-personas-korea:dispatch-strategy` with the Section A definition as the persona filter.
