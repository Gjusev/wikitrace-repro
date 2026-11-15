"""Offline bench: mechanism direction + determinism + honest labeling."""

import unittest

from wikitrace_repro.agent import MODE_INSIGHTS_ONLY, MODE_NO_MEMORY, MODE_WIKITRACE
from wikitrace_repro.bench import build_corpus, run_bench, run_mode


class TestCorpus(unittest.TestCase):
    def test_corpus_chain_is_complete(self):
        store = build_corpus()
        self.assertGreater(len(store), 0)
        for lesson in store.all_lessons():
            # every lesson can walk both links without KeyError
            store.trajectory_for_lesson(lesson.lesson_id)
            store.diagnosis_for_lesson(lesson.lesson_id)

    def test_corpus_contains_all_three_triggers(self):
        from wikitrace_repro.detector import detect
        store = build_corpus()
        summaries = [detect(store, l).summary() for l in store.all_lessons()]
        self.assertTrue(any("incomplete" in s for s in summaries), summaries)
        self.assertTrue(any("failure-sourced" in s for s in summaries), summaries)
        self.assertTrue(any("conflicts:" in s for s in summaries), summaries)


class TestBenchDirection(unittest.TestCase):
    """The mechanism claim: links turn a degrading memory into a safe one."""

    def setUp(self):
        self.no_mem = run_mode(MODE_NO_MEMORY)
        self.blind = run_mode(MODE_INSIGHTS_ONLY)
        self.linked = run_mode(MODE_WIKITRACE)

    def test_no_memory_solves_everything(self):
        self.assertEqual(self.no_mem.successes, self.no_mem.tasks)
        self.assertEqual(self.no_mem.degradation, 0)

    def test_blind_memory_degrades(self):
        """Insights without links must degrade the stub agent (paper's finding)."""
        self.assertGreater(self.blind.degradation, 0)
        self.assertGreater(self.blind.wrong_lesson_followed, 0)
        self.assertLess(self.blind.successes, self.no_mem.successes)

    def test_evidence_links_remove_degradation(self):
        self.assertEqual(self.linked.successes, self.no_mem.successes)
        self.assertEqual(self.linked.degradation, 0)
        self.assertEqual(self.linked.wrong_lesson_followed, 0)

    def test_links_beat_blind_on_every_metric(self):
        self.assertGreater(self.linked.successes, self.blind.successes)
        self.assertLess(self.linked.wrong_lesson_followed, self.blind.wrong_lesson_followed)
        self.assertLess(self.linked.degradation, self.blind.degradation)


class TestReport(unittest.TestCase):
    def test_determinism(self):
        self.assertEqual(run_bench(), run_bench())

    def test_report_is_labeled_as_harness_validation(self):
        report = run_bench()
        self.assertIn("HARNESS VALIDATION", report)
        self.assertIn("NOT a reproduction", report)

    def test_report_contains_all_modes(self):
        report = run_bench()
        for mode in (MODE_NO_MEMORY, MODE_INSIGHTS_ONLY, MODE_WIKITRACE):
            self.assertIn(mode, report)


if __name__ == "__main__":
    unittest.main()
