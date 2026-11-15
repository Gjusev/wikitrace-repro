# wikitrace-repro

Offline repro/test harness for **WikiTrace** — evidence-linked memory that
reduces memory-induced degradation in LLM agents.

> Lee, Choi, Baek, Hwang (KAIST AI / DeepAuto.ai), *"Don't Just Trust Your
> Memory: Evidence-Linked Memory Reduces Memory-Induced Degradation in LLM
> Agents"*, [arXiv:2611.14320](https://arxiv.org/abs/2611.14320) · official
> code: [yukyeongleee/wikitrace](https://github.com/yukyeongleee/wikitrace)
> (Apache-2.0). **Independent, unofficial repro — not affiliated with the
> authors.**

The paper's finding: an agent's memory can make it **fail a task it would
solve without memory**. Lessons are distilled from runs labeled only
success/failure and stored *without the run itself* — so a wrong lesson
cannot be verified. WikiTrace links every lesson (insight) to the diagnosis
of why its run succeeded/failed and to the raw trajectory, and the agent
walks those links whenever a lesson is incomplete, conflicts with another,
or comes from a failure — before acting.

## Honest status

| Claim | Status |
|---|---|
| Evidence-chain mechanism (lesson → diagnosis → trajectory) implemented, offline-tested | ✅ this repo |
| Mandatory evidence links enforced at write time | ✅ this repo |
| Degradation detector (incomplete / conflicting / failure-sourced) | ✅ this repo |
| Link-walking pre-action check | ✅ this repo |
| Offline synthetic bench showing degradation drop on stub data | ✅ this repo — **harness validation, not benchmark results** |
| Paper's benchmark numbers (ALFWorld, ScienceWorld, PlanCraft, AppWorld, tau3) | ❌ **not reproduced** — needs real-model runs (see ROADMAP) |

The offline bench uses a **deterministic rule agent on synthetic tasks**.
It validates that the mechanism works end-to-end; it says nothing about the
paper's +10.7 / 6.5%→4.5% numbers.

## Existing implementations

First open lightweight/offline repro of the mechanism — see [NOTES.md](NOTES.md)
for the full search (2026-11-15): no third-party repro existed; only the
official Apache-2.0 harness (which requires Python 3.11+/uv, Node 20, Docker,
and paid LLM runs) plus news coverage and paper reviews.

## Quickstart

Zero dependencies; Python ≥ 3.9.

```bash
python3 -m unittest          # 39 tests, fully offline
python3 scripts/run_bench.py # offline stub degradation bench
```

Bench output (committed at `results/offline-stub-bench.txt`):

```
HARNESS VALIDATION -- offline stub bench (deterministic rule agent,
synthetic tasks). This is NOT a reproduction of the paper's benchmark
numbers; it validates that the evidence-chain mechanism works offline.

Memory-induced degradation = tasks the no-memory agent solves but the
memory mode fails.

mode               success   wrong-lesson   degradation
-------------------------------------------------------
no-memory              8/8            0/8           0/8
insights-only          4/8            4/8           4/8
wikitrace              8/8            0/8           0/8

Mechanism check:
  degradation, insights-only vs wikitrace: 4 -> 0
  wrong-lesson rate, insights-only vs wikitrace: 50.0% -> 0.0%
```

Same insights, with vs. without evidence links: degradation **4/8 → 0/8**,
wrong-lesson-followed rate **50.0% → 0.0%** on stub data.

## Layout

```
wikitrace_repro/
  store.py      LessonStore — insight → diagnosis → trajectory, links mandatory
  detector.py   incomplete / conflicting / failure-sourced flags
  walker.py     link-walking pre-action check: act / recover / refuse
  agent.py      deterministic stub agent; modes: no-memory, insights-only, wikitrace
  bench.py      synthetic degradation bench (HARNESS VALIDATION)
  zai.py        real-model access — Z.ai Coding Plan ONLY, glm-5.3-flash ONLY
tests/          39 offline tests (incl. self-exclusion + billing-STOP tests)
scripts/        run_bench.py
results/        committed bench output
NOTES.md        existing-implementation check + official-repo survey
ROADMAP.md      next steps; item 1 = first real-model run (money-gated)
CONTINUE.md     agent handoff rules + STOP point
```

## Findings so far

- The degradation triggers from the paper map cleanly onto checkable
  predicates: *incomplete* → elided parameter markers (`<service>`, `...`,
  `TODO`); *conflicting* → same context, different action; *failure-sourced*
  → diagnosis outcome / trajectory success. All three are detectable without
  an LLM.
- Conflict detection must **exclude the lesson under consideration from its
  own comparison set** — otherwise a freshly stored lesson conflicts with
  itself at similarity 1.0 and every lesson looks flagged. There is a test
  (`test_no_self_conflict`) that pins this.
- Order matters in the walker: failure-sourced → conflict → incomplete. A
  lesson that is both incomplete and failure-sourced must be refused, not
  "repaired" from a trajectory that itself failed.
- Conflict resolution by *successful source trajectory* is enough to pick the
  right lesson in a conflicting pair — but when both sources succeeded with
  different actions, the only safe move is refusing both (test:
  `test_unresolvable_conflict_refused`).

## Real-model runs (owner-gated)

LLM runs go **only** through the Z.ai Coding Plan, model **`glm-5.3-flash`
only**, key in `WIKITRACE_ZAI_KEY`:

```bash
export WIKITRACE_ZAI_KEY=...        # Z.ai Coding Plan key
# endpoint: https://api.z.ai/api/coding/paas/v4  (pinned in wikitrace_repro/zai.py)
```

On a billing/auth/endpoint error: **STOP and report — never fall back** to
another provider or model. Real runs require owner approval (ROADMAP item 1).

## Synergy

Pairs with **arXiv:2611.11929 (SoMem)** — evidence-linking for agent memory.
WikiTrace supplies the link-and-descend structure; SoMem's retention ideas
cover what gets linked over long horizons. A combined store is a ROADMAP
direction.

## License

MIT (this repo). The paper is CC BY 4.0; the official implementation is
Apache-2.0.
