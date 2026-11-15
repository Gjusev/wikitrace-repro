# CONTINUE.md — read this first when an agent picks up this repo

## What this repo is

Offline repro/test harness for WikiTrace (arXiv:2611.14320, KAIST —
evidence-linked agent memory that reduces memory-induced degradation).
Mechanism implemented + offline-tested: mandatory lesson → diagnosis →
trajectory links, degradation detector, link-walking pre-action check, and
an offline stub bench (HARNESS VALIDATION ONLY). The paper's benchmark
numbers are **not** reproduced. Read README.md and ROADMAP.md fully.

## Working rules

- **Offline-first**: the test suite stays zero-dependency and passes with
  `python3 -m unittest` from the repo root (39 tests). Network imports stay
  lazy inside the method that uses them (`wikitrace_repro/zai.py`).
- **Honest claims**: never state benchmark numbers that haven't been run.
  The stub bench is harness validation, not a benchmark result — keep the
  HARNESS VALIDATION label on any output derived from it. Anything measured
  goes in README/results with the exact command that produced it.
- Cite the paper first (arXiv:2611.14320); independent, unofficial
  implementation — never imply affiliation with the authors.
- Commits in English, conventional-commit style (feat:/fix:/docs:).
- Before pushing: run the full offline suite; it must be green.
- **Models — Z.ai Coding Plan (mandatory, no other provider/model)**:

```bash
export WIKITRACE_ZAI_KEY="<Z.ai Coding Plan key>"
# endpoint (pinned in wikitrace_repro/zai.py): https://api.z.ai/api/coding/paas/v4
# model (pinned): glm-5.3-flash ONLY — never use or document an alternative
```

  Flat subscription: on a billing/auth/endpoint error (401/402/403/429) STOP
  and report — do NOT switch providers or models to "get it working"
  (`zai.ZaiBillingStop` enforces this; keep it that way).

- **Real-model runs are owner-approval-gated.** Do not spend plan quota
  without explicit owner approval; the offline suite and bench never call
  the network and must stay that way.

## Current task (do this now)

Implement ROADMAP.md item 1 — the first real-model degradation probe — but
**prepare it, do not run it** without owner approval:

1. Add `wikitrace_repro/llm_agent.py`: an LLM-backed agent with the same
   `solve(Task) -> Step` interface as `StubAgent`, using `zai.chat()` for
   the decision and `LinkWalker` for the pre-action check. Acceptance: its
   offline tests pass with a scripted fake `chat`.
2. Add `scripts/run_real_probe.py`: runs the three modes over the synthetic
   task set with the real model, writes `results/real/<timestamp>/`, prints
   the summary. Acceptance: `--dry-run` (default) prints the plan and makes
   zero network calls; a real run requires `--i-have-owner-approval`.
3. Run the offline suite: `python3 -m unittest` — must stay green.

STOP POINT: if no live endpoint/key is available or owner approval for a
real run is not given, commit the prepared tooling with `results/real/`
marked "not yet run" and stop there. Do not attempt a real run and do not
fall back to any other provider or model.

## After that

Follow ROADMAP.md in order. One item per commit series.
