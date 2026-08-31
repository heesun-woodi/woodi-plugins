# Designing survey items for synthetic (LLM-persona) respondents

The respondents here are not people — they are LLM personas from `nemotron-personas-korea`
role-playing Korean adults. They answer fast, cheaply, and at scale, but they answer
*differently* from humans. Design to their grain and the data is genuinely useful; ignore it
and you get confident-looking noise.

## Where synthetic respondents are trustworthy vs. not

| Item type | Reliability | Use it for |
|---|---|---|
| Likert scale (explicit anchors) | High | Load-bearing measurements — the ones a decision hinges on |
| Binary / single-choice | High | Clear either/or judgments, screening |
| Multiple-choice / ranking | Medium-High | Prioritization ("rank top 3") |
| Open-ended free text | Low for counts, high for texture | Voice-of-customer language, themes, phrasing — not distributions |

**Rule of thumb:** put your decision weight on closed-form items. Use open-ended items to
*explain* the closed-form pattern and to harvest the respondent's own words (which are gold for
later marketing copy), but don't compute percentages from them and treat those as population truth.

## Likert anchors: write them explicitly and symmetrically

Synthetic respondents are far more anchor-sensitive than humans. A scale labeled only "1–5"
invites clustering and drift. Always spell out both poles and a real neutral midpoint:

```
1 = 전혀 그렇지 않다   2 = 그렇지 않다   3 = 보통이다   4 = 그렇다   5 = 매우 그렇다
```

- Keep the steps evenly spaced in wording (don't jump from "그렇지 않다" straight to "매우 그렇다").
- Use the **same** anchor set across a battery so items are comparable.
- 5-point is the safe default. 7-point only when you genuinely need finer resolution and the
  anchors stay unambiguous.

## Debias the wording — personas are eager to please

LLM personas have a strong acquiescence / please-the-asker tendency. Counter it:

- **No leading stems.** "이 서비스가 왜 매력적이라고 생각하시나요?" presupposes appeal. Ask
  "이 서비스에 대해 어떻게 느끼시나요?" or measure appeal on a scale that includes low options.
- **Balance the keying.** In any battery, mix positively-keyed items ("이것이 매력적이다") with
  negatively-keyed ones ("이것이 망설여진다"). All-positive batteries slide toward the ceiling.
- **Don't telegraph the desired answer.** If the "right" choice is obvious from the phrasing, the
  persona will pick it regardless of the character it's playing.
- **Offer a genuine out.** Include "잘 모르겠다 / 해당 없음" where forcing an opinion would
  manufacture false signal.

## Audience definition = persona filter

The Phase 0 target audience is not just framing — it becomes the concrete filter that selects
which personas answer (age, life-stage, role, region, household). Capture it in filterable terms
so the handoff to `nemotron-personas-korea:dispatch-strategy` is clean. Vague audiences ("young
people") produce vague persona samples; specific ones ("만 1~2세 자녀를 둔 수도권 맞벌이 부모")
produce a sample you can actually reason about.

## Validity check before you trust results

When results come back (via the dispatch skill), sanity-check them the way you would any
synthetic-vs-real comparison: do the marginals look plausible for the real population? Is the
distribution shape too tight (a tell-tale sign of persona clustering)? For the full methodology,
`nemotron-personas-korea:synthetic-population-validity` is the reference — but the design-time
takeaway is simpler: **closed-form + explicit anchors + debiased wording** is what makes the
downstream results worth validating at all.
