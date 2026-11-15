"""Degradation detector: incomplete / conflicting / failure-sourced flags."""

import unittest

from wikitrace_repro.detector import detect, is_incomplete
from wikitrace_repro.store import Diagnosis, Lesson, LessonStore, Trajectory


def _add_run(store, run_id, diag_id, lesson_id, *, outcome, success,
             context, action, text):
    store.add_trajectory(Trajectory(run_id, "task", ("s",),
                                    final_action=action, success=success))
    store.add_diagnosis(Diagnosis(diag_id, run_id, outcome=outcome, cause="c"))
    store.add_lesson(Lesson(lesson_id, text, context_key=context, action=action,
                            diagnosis_id=diag_id, trajectory_id=run_id))
    return store


def _two_lesson_store():
    """Migrate-style conflict: wrong lesson (from a failed run) inserted first."""
    store = LessonStore()
    _add_run(store, "run-ok", "diag-ok", "migrate-right", outcome="success",
             success=True, context="migrate", action="alembic upgrade head",
             text="For migrate tasks run alembic upgrade head.")
    _add_run(store, "run-fail", "diag-fail", "migrate-wrong", outcome="failure",
             success=False, context="migrate", action="alembic downgrade base",
             text="For migrate tasks run alembic downgrade base.")
    return store


class TestDetector(unittest.TestCase):
    def test_incomplete_marker_detection(self):
        self.assertTrue(is_incomplete("run systemctl restart <service>"))
        self.assertTrue(is_incomplete("TODO: fill in the region"))
        self.assertTrue(is_incomplete("scale web --replicas ..."))
        self.assertFalse(is_incomplete("run systemctl restart postgresql"))

    def test_clean_lesson_unflagged(self):
        store = _two_lesson_store()
        flags = detect(store, store.lesson("migrate-right"))
        # conflicts with migrate-wrong, but is complete and success-sourced
        self.assertFalse(flags.incomplete)
        self.assertFalse(flags.failure_sourced)
        self.assertEqual(flags.conflicting_with, ("migrate-wrong",))
        self.assertTrue(flags.flagged)

    def test_failure_sourced_flagged(self):
        store = _two_lesson_store()
        flags = detect(store, store.lesson("migrate-wrong"))
        self.assertTrue(flags.failure_sourced)

    def test_conflict_detection(self):
        store = _two_lesson_store()
        self.assertEqual(detect(store, store.lesson("migrate-right")).conflicting_with,
                         ("migrate-wrong",))
        self.assertEqual(detect(store, store.lesson("migrate-wrong")).conflicting_with,
                         ("migrate-right",))

    def test_no_self_conflict(self):
        """A single lesson must not conflict with itself (self-exclusion)."""
        store = LessonStore()
        _add_run(store, "run-1", "diag-1", "only", outcome="success", success=True,
                 context="solo", action="do it", text="Do it.")
        flags = detect(store, store.lesson("only"))
        self.assertEqual(flags.conflicting_with, ())
        self.assertFalse(flags.flagged)

    def test_incomplete_lesson_flagged(self):
        store = LessonStore()
        _add_run(store, "run-1", "diag-1", "vague", outcome="success", success=True,
                 context="restart", action="systemctl restart <service>",
                 text="Run systemctl restart <service>.")
        self.assertTrue(detect(store, store.lesson("vague")).incomplete)

    def test_flag_summary(self):
        store = _two_lesson_store()
        self.assertIn("failure-sourced",
                      detect(store, store.lesson("migrate-wrong")).summary())
        self.assertEqual(detect(store, store.lesson("migrate-right")).summary(),
                         "conflicts:migrate-wrong")


if __name__ == "__main__":
    unittest.main()
