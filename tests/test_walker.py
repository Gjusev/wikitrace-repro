"""Link walker: act / recover / refuse decisions from evidence links."""

import unittest

from wikitrace_repro.store import Diagnosis, Lesson, LessonStore, Trajectory
from wikitrace_repro.walker import LinkWalker


def _store_with(lesson_id, *, outcome, success, context, action, text,
                final_action=None, run_id=None, diag_id=None):
    store = LessonStore()
    run_id = run_id or f"run-{lesson_id}"
    diag_id = diag_id or f"diag-{lesson_id}"
    store.add_trajectory(Trajectory(run_id, "task", ("s",),
                                    final_action=final_action or action,
                                    success=success))
    store.add_diagnosis(Diagnosis(diag_id, run_id, outcome=outcome, cause="c"))
    store.add_lesson(Lesson(lesson_id, text, context_key=context, action=action,
                            diagnosis_id=diag_id, trajectory_id=run_id))
    return store


class TestLinkWalker(unittest.TestCase):
    def test_clean_lesson_acted_on_without_walk(self):
        store = _store_with("good", outcome="success", success=True,
                            context="deploy", action="deploy api --canary",
                            text="Deploy with deploy api --canary.")
        verdict = LinkWalker(store).pre_action_check(store.lesson("good"))
        self.assertTrue(verdict.acted_on_lesson)
        self.assertFalse(verdict.walked_links)
        self.assertEqual(verdict.action, "deploy api --canary")

    def test_incomplete_recovered_from_trajectory(self):
        store = _store_with(
            "elided", outcome="success", success=True, context="restart",
            action="systemctl restart <service>",
            text="Run systemctl restart <service>.",
            final_action="systemctl restart postgresql")
        verdict = LinkWalker(store).pre_action_check(store.lesson("elided"))
        self.assertTrue(verdict.acted_on_lesson)
        self.assertTrue(verdict.walked_links)
        self.assertEqual(verdict.action, "systemctl restart postgresql")

    def test_failure_sourced_refused(self):
        store = _store_with("bad", outcome="failure", success=False,
                            context="cache", action="redis-cli FLUSHDB",
                            text="Run redis-cli FLUSHDB.")
        verdict = LinkWalker(store).pre_action_check(store.lesson("bad"))
        self.assertFalse(verdict.acted_on_lesson)
        self.assertTrue(verdict.walked_links)
        self.assertIn("refused", verdict.reason)

    def test_incomplete_from_failed_run_refused(self):
        store = _store_with(
            "vague-bad", outcome="failure", success=False, context="scale",
            action="scale web --replicas <n>",
            text="Run scale web --replicas <n>.",
            final_action="scale web --replicas 4")
        verdict = LinkWalker(store).pre_action_check(store.lesson("vague-bad"))
        self.assertFalse(verdict.acted_on_lesson)

    def test_conflict_resolved_via_successful_trajectory(self):
        store = LessonStore()
        for lesson_id, run_id, diag_id, action, success, outcome in (
            ("migrate-wrong", "run-f", "diag-f", "alembic downgrade base", False, "failure"),
            ("migrate-right", "run-s", "diag-s", "alembic upgrade head", True, "success"),
        ):
            store.add_trajectory(Trajectory(run_id, "t", ("s",), final_action=action,
                                            success=success))
            store.add_diagnosis(Diagnosis(diag_id, run_id, outcome=outcome, cause="c"))
            store.add_lesson(Lesson(lesson_id, f"Run {action}.", context_key="migrate",
                                    action=action, diagnosis_id=diag_id,
                                    trajectory_id=run_id))
        walker = LinkWalker(store)
        wrong = walker.pre_action_check(store.lesson("migrate-wrong"))
        right = walker.pre_action_check(store.lesson("migrate-right"))
        # the failure-sourced wrong lesson is refused outright
        self.assertFalse(wrong.acted_on_lesson)
        # the right lesson's conflict resolves to the successful trajectory's action
        self.assertTrue(right.acted_on_lesson)
        self.assertEqual(right.action, "alembic upgrade head")

    def test_unresolvable_conflict_refused(self):
        """Both conflicting lessons success-sourced with different actions -> refuse."""
        store = LessonStore()
        for lesson_id, run_id, diag_id, action in (
            ("a", "run-a", "diag-a", "cmd a"),
            ("b", "run-b", "diag-b", "cmd b"),
        ):
            store.add_trajectory(Trajectory(run_id, "t", ("s",), final_action=action,
                                            success=True))
            store.add_diagnosis(Diagnosis(diag_id, run_id, outcome="success", cause="c"))
            store.add_lesson(Lesson(lesson_id, f"Run {action}.", context_key="x",
                                    action=action, diagnosis_id=diag_id,
                                    trajectory_id=run_id))
        verdict = LinkWalker(store).pre_action_check(store.lesson("a"))
        self.assertFalse(verdict.acted_on_lesson)
        self.assertIn("could not be resolved", verdict.reason)


if __name__ == "__main__":
    unittest.main()
