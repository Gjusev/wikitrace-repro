# NOTES.md — existing-implementation check (2026-11-15)

## Step 1: are there third-party repros of WikiTrace?

**Verdict: none found.** Searches (`"wikitrace" github reproduction fork
implementation -yukyeongleee`, plus paper-title and arXiv-ID queries) surfaced
only:

- **The official repo** — [yukyeongleee/wikitrace](https://github.com/yukyeongleee/wikitrace)
  (Apache-2.0), linked from the paper.
- **News / digest coverage** — DAIR.AI post, TokenPost, HyperAI, The Agent
  Times, AGI Hunt: none ship code.
- **Paper reviews** — sgtcho.com (an independent *audit/arithmetic check* of
  released numbers, explicitly "does not establish that this article has
  executed the full benchmark harness"), machinoai.in, aimap.page, dev.to
  explainer: analysis only, no implementations.
- **Name collisions, unrelated** — RobertoReale/WikiTrace (Wikipedia-history
  browser extension), lucwl's `wikitrace` (NLP Wikipedia paths).

So this repo is the **first open lightweight/offline repro** of the
evidence-chain mechanism. Stated as such in the README.

## Official repo, as shallow-cloned (commit `25a83679af0eb67ab3c835ab920d3a243fb80845`, 2026-10-14)

Read-only inspection, not a fork. Structure:

```
configs/        one YAML per suite (alfworld, appworld, plancraft, scienceworld, tau3) + base.yaml
docker/         sandbox image (--network none) + per-benchmark envs
src/wikitrace/
  memory/       the paper's corpus: store.py (on-disk raw layer + indexes,
                480 LOC), compiler.py (run -> compilation + <=3 insights,
                380 LOC), insights.py, mount.py (read-only mount),
                rawturns.py, citation.py, recommend.py, prompts/
  envs/         per-benchmark adapters (appworld, tau3, textgame: alfworld/
                scienceworld/plancraft), workflows, benchmarks
tools/          pi-patches (pinned Pi terminal-agent patches)
tests/          unit / regression / integration / fixtures / analysis
docs/           project site
```

Dependencies: Python 3.11+, `uv`, **Node 20 and Docker** required for the full
harness. Python deps: typer, pydantic, pyyaml, httpx, jinja2 (+ numpy/pandas/
scipy/matplotlib for analysis; pytest/ruff for dev). CLI is three steps:
`build` (train-run memory, `outputs/corpus/`), `run` (`--method no-memory |
kinj | wikitrace`), `analyze` (Gain/Regression vs No Memory). Memory built
under a different config/commit is refused (staleness guard).

Headline numbers (paper): +10.7 pts over no-memory across five benchmarks;
memory-induced regression (share of previously-solved tasks the memory agent
fails) drops 6.5% → 4.5%.

## What this repo adds

The official harness needs Docker, Node, benchmark envs and paid LLM calls —
none of it is testable offline. This repro adds:

1. **stdlib-only core** — no dependencies, `python3 -m unittest` from root.
2. **Offline-testable evidence chain** — the full lesson → diagnosis →
   trajectory chain with enforced mandatory links (the store *refuses* an
   unlinkaged lesson, the failure mode the paper identifies).
3. **Degradation detector** — incomplete / conflicting / failure-sourced
   flags, with a self-exclusion test (a lesson must not conflict with itself).
4. **Link-walking pre-action check** — act / recover-from-trajectory /
   refuse decisions, fully deterministic.
5. **Offline synthetic degradation bench** — stub agent, 8 tasks, labeled
   HARNESS VALIDATION: degradation 4/8 (insights-only) → 0/8 (wikitrace).

## Synergy note

WikiTrace pairs naturally with **arXiv:2611.11929 (SoMem)**, which also
concerns evidence-linking for agent memory: WikiTrace supplies the
*link-and-descend* structure (insight → compilation → raw trajectory),
SoMem's evidence-linking ideas cover *what* gets linked and retained over
long horizons. A combined store (SoMem retention policy over WikiTrace-style
links) is listed in ROADMAP.md as a future direction.

## Citation

Lee, Choi, Baek, Hwang (KAIST AI / DeepAuto.ai), "Don't Just Trust Your
Memory: Evidence-Linked Memory Reduces Memory-Induced Degradation in LLM
Agents", arXiv:2611.14320. Code: github.com/yukyeongleee/wikitrace (Apache-2.0).
This repo is independent and unofficial; not affiliated with the authors.
