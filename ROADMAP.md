# ROADMAP.md — ordered next steps

1. **First real-model run (MONEY-GATED — owner approval required before
   running).** Wire `wikitrace_repro/zai.py` (Z.ai Coding Plan,
   `https://api.z.ai/api/coding/paas/v4`, model `glm-5.3-flash`, key in
   `WIKITRACE_ZAI_KEY`) into a small real degradation probe: have the model
   answer synthetic ops tasks with the same three memory modes
   (no-memory / insights-only / wikitrace-verified) used by the stub bench,
   ~20 tasks, and compare success + wrong-lesson-followed rates. Replace the
   stub agent with an LLM-backed one behind the same `solve()` interface.
   Owner rules: billing/auth/endpoint error → STOP and report, never fall
   back to another provider or model. Record the exact command + raw output
   under `results/real/`.
2. **Scale the synthetic bench.** More tasks, multiple memory sizes, and a
   second degradation axis (stale lessons: evidence from an older env
   version). Add per-trigger ablation: which trigger (incomplete /
   conflicting / failure-sourced) contributes most degradation?
3. **Cross-check against the official harness configs** (see NOTES.md):
   mirror their Gain/Regression metric definitions exactly so future real
   runs are directly comparable with the paper's `analyze` step.
4. **LLM-judged compiler.** The synthetic corpus is hand-written; add an
   optional LLM-backed compiler (Z.ai plan only) that turns a trajectory
   into insight + diagnosis, with the store still enforcing mandatory links.
5. **SoMem combination (arXiv:2611.11929).** SoMem retention policy over a
   WikiTrace-style link structure — what gets kept vs. what gets linked.
6. **CI.** GitHub Actions running `python3 -m unittest` on 3.9–3.13.
