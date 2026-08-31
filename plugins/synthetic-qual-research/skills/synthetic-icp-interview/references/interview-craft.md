# Interview craft (deep in-character interviews with live probes)

You're in `nemotron-personas-korea:persona-interviewee` mode: Claude plays the confirmed persona in
character, the user is the interviewer. This file is the craft that turns that mode from a Q&A into a
qualitative interview that actually surfaces the *why*.

## The interviewer's shape: funnel + follow the emotion

- **Open easy.** A self-intro or a recent concrete episode. Warm, low-stakes, gets the persona
  talking in specifics. Don't lead with the decision question.
- **Funnel from broad to deep.** Each question narrows on what the last answer revealed. You are not
  marching through a fixed list — the list is a fallback; the *live answer* is the map.
- **Follow the emotion, not the topic.** When a persona's answer carries feeling — frustration,
  guilt, relief, a small pride — that's the thread to pull. Feelings sit on top of needs.
- **Ladder down to values.** The technique: behavior → feeling → value.
  - "지금 돌봄 구조가 어떻게 되세요?" (behavior)
  - → "그게 자주 바뀌면 어떠세요?" (feeling)
  - → "아이한테 안정감이 왜 그렇게 중요하세요?" (value)
  The richest material is usually three "why"s below the opening answer. Most interviews stop one
  question too early; go one deeper than feels natural.
- **Ask the question no one asks them.** Somewhere mid-interview, turn the lens: not "is this good
  for your child" (they've rehearsed that) but "is this good for *you*?" The unrehearsed question is
  where the real, un-pre-processed answer lives — and it's usually the emotional peak.

## The live probe recommendation (the built-in practice)

After **every** in-character answer, append a clearly-marked block recommending the next 2–3
questions. This is the signature of this skill — it turns the interview into a guided instrument so
the interviewer always has a sharp next move and understands *why* it's sharp.

Format (keep it in the meta-channel — a blockquote or brackets — never in the persona's voice):

```
> [추천 질문 N개]
>
> 1. **<what this probe targets>** — "<the actual question to ask>"
>    → <one line: what insight it unlocks and how it serves the goal>
> 2. ...
```

What makes a *good* recommended probe:
- **It targets a specific unknown**, not "tell me more." Name what you're trying to learn.
- **It ties to the decision.** Each probe should, if answered, move the Phase 0 goal — e.g. "reveals
  whether the participation barrier is a dealbreaker or negotiable," which the 설명회 messaging needs.
- **It offers a mix of altitudes.** One probe that goes *deeper* on the current thread, one that
  opens an *adjacent* area, one that tests a *hypothesis* you're forming. That spread keeps the
  interviewer in control of pace and direction.
- **It escalates toward the peak.** As the interview matures, let the probes get braver — the
  "is this good for you?" class of question belongs later, once trust is built.

Why this works: the interviewer (the user) may not be a trained researcher. Handing them
decision-linked next questions after each answer means the interview stays sharp even if they'd
otherwise ask flat follow-ups. And explaining *why* each probe matters teaches the method as it runs.

## The bracket convention (don't collide with persona-interviewee)

In `persona-interviewee`, text the *interviewer* puts in `[square brackets]` is a meta-instruction to
Claude (stage direction: `[switch to phone]`, `[quit interview]`), not a question to the persona.
Your probe-recommendation blocks flow the other way — from Claude to the interviewer — so mark them
as a blockquote or a `> [추천 질문]` header so they read as suggestions, not as the persona speaking
and not as interviewer stage-directions. The persona's own voice never appears in brackets. Keep the
two channels visually distinct so the transcript stays legible.

## Peak-end steering

People remember an experience by its emotional **peak** and its **end**, not its average. Two
implications for how you run the interview:
- **Engineer at least one peak.** The unrehearsed question, the moment the persona realizes
  something mid-sentence ("...그 질문은 생각 안 해봤어요"). Don't rush past it — let it breathe.
- **Close by reflecting, not interrogating.** End with something like "오늘 얘기해보니 어떠세요?" —
  let the persona metabolize the conversation. That reflection often contains the cleanest statement
  of their real state of mind, and it's the note the whole interview will be remembered by.

## Handing off to synthesis

Keep a running eye on Phase 4 while you interview: when the persona says something that names a
**latent need**, a **decisive tension**, or a **decision implication**, note it. The synthesis is
easier to write if you've been collecting the load-bearing quotes as they land rather than
reconstructing them afterward.
