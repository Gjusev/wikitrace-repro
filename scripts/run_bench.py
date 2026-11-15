#!/usr/bin/env python3
"""Run the offline stub degradation bench and save the report.

Usage: python3 scripts/run_bench.py
No network, no API key, no dependencies.
"""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from wikitrace_repro.bench import run_bench  # noqa: E402


def main() -> int:
    report = run_bench()
    print(report)
    out = pathlib.Path(__file__).resolve().parents[1] / "results" / "offline-stub-bench.txt"
    out.parent.mkdir(exist_ok=True)
    out.write_text(report + "\n", encoding="utf-8")
    print(f"\nsaved: {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
