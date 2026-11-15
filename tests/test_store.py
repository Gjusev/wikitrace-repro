"""Evidence-link enforcement in the LessonStore."""

import unittest

from wikitrace_repro.store import (
    Diagnosis,
    Lesson,
    LessonStore,
    MissingEvidenceLink,
    Trajectory,
)


def _trajectory(run_id="run-1", success=True):
    return Trajectory(run_id, "task", ("step one",), final_action="do thing", success=success)


def _diagnosis(diag_id="diag-1", run_id="run-1", outcome="success"):
    return Diagnosis(diag_id, run_id, outcome=outcome, cause="because")


def _lesson(**overrides):
    kwargs = dict(
        lesson_id="lesson-1",
        text="For tasks like this, do thing.",
        context_key="ops",
        action="do thing",
        diagnosis_id="diag-1",
        trajectory_id="run-1",
    )
    kwargs.update(overrides)
    return Lesson(**kwargs)


class TestStore(unittest.TestCase):
    def test_full_chain_accepted(self):
        store = _populated()
        self.assertEqual(len(store), 1)
        self.assertEqual(store.lesson("lesson-1").action, "do thing")

    def test_lesson_without_any_links_rejected(self):
        store = _populated()
        with self.assertRaises(MissingEvidenceLink):
            store.add_lesson(_lesson(diagnosis_id="", trajectory_id=""))

    def test_lesson_with_missing_diagnosis_link_rejected(self):
        store = _populated()
        with self.assertRaises(MissingEvidenceLink):
            store.add_lesson(_lesson(diagnosis_id="nope"))

    def test_lesson_with_missing_trajectory_link_rejected(self):
        store = _populated()
        with self.assertRaises(MissingEvidenceLink):
            store.add_lesson(_lesson(trajectory_id="nope"))

    def test_diagnosis_for_unknown_run_rejected(self):
        store = LessonStore()
        store.add_trajectory(_trajectory())
        with self.assertRaises(MissingEvidenceLink):
            store.add_diagnosis(_diagnosis(run_id="ghost-run"))

    def test_duplicate_run_id_rejected(self):
        store = LessonStore()
        store.add_trajectory(_trajectory())
        with self.assertRaises(ValueError):
            store.add_trajectory(_trajectory())

    def test_link_walk_helpers(self):
        store = _populated()
        self.assertEqual(store.trajectory_for_lesson("lesson-1").run_id, "run-1")
        self.assertEqual(store.diagnosis_for_lesson("lesson-1").diagnosis_id, "diag-1")

    def test_lessons_for_insertion_order(self):
        store = _populated()
        store.add_trajectory(_trajectory("run-2", success=False))
        store.add_diagnosis(_diagnosis("diag-2", "run-2", outcome="failure"))
        store.add_lesson(_lesson(lesson_id="lesson-0", diagnosis_id="diag-2",
                                 trajectory_id="run-2"))
        ids = [l.lesson_id for l in store.lessons_for("ops")]
        self.assertEqual(ids, ["lesson-1", "lesson-0"])


def _populated():
    store = LessonStore()
    store.add_trajectory(_trajectory())
    store.add_diagnosis(_diagnosis())
    store.add_lesson(_lesson())
    return store


if __name__ == "__main__":
    unittest.main()
