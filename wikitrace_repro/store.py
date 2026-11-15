"""Evidence-linked lesson store.

Mirrors WikiTrace's three-layer corpus (arXiv:2611.14320): every lesson
(insight) MUST carry two evidence links -- the diagnosis of the run that
produced it and the raw trajectory of that run. Storing a lesson without
its originating execution is exactly the failure mode the paper identifies,
so this store refuses it.
"""

from __future__ import annotations

from dataclasses import dataclass


class MissingEvidenceLink(ValueError):
    """Raised when a record is stored without a resolvable evidence link."""


@dataclass(frozen=True)
class Trajectory:
    """Raw execution record of one run (the paper's raw layer)."""

    run_id: str
    task: str
    steps: tuple[str, ...]
    final_action: str
    success: bool


@dataclass(frozen=True)
class Diagnosis:
    """Why the source run succeeded or failed (the paper's compilation layer)."""

    diagnosis_id: str
    run_id: str
    outcome: str  # "success" | "failure"
    cause: str


@dataclass(frozen=True)
class Lesson:
    """A concise insight distilled from one run (the paper's insight layer).

    ``diagnosis_id`` and ``trajectory_id`` are mandatory.
    """

    lesson_id: str
    text: str
    context_key: str
    action: str
    diagnosis_id: str
    trajectory_id: str


class LessonStore:
    """In-memory corpus with enforced insight -> diagnosis -> trajectory links."""

    def __init__(self) -> None:
        self._trajectories: dict[str, Trajectory] = {}
        self._diagnoses: dict[str, Diagnosis] = {}
        self._lessons: dict[str, Lesson] = {}

    # -- writes ------------------------------------------------------------

    def add_trajectory(self, trajectory: Trajectory) -> None:
        if trajectory.run_id in self._trajectories:
            raise ValueError(f"duplicate run_id: {trajectory.run_id}")
        self._trajectories[trajectory.run_id] = trajectory

    def add_diagnosis(self, diagnosis: Diagnosis) -> None:
        if diagnosis.run_id not in self._trajectories:
            raise MissingEvidenceLink(
                f"diagnosis {diagnosis.diagnosis_id} links to unknown run {diagnosis.run_id}"
            )
        self._diagnoses[diagnosis.diagnosis_id] = diagnosis

    def add_lesson(self, lesson: Lesson) -> None:
        if not lesson.diagnosis_id or not lesson.trajectory_id:
            raise MissingEvidenceLink(
                f"lesson {lesson.lesson_id} stored without evidence links: "
                "every lesson needs a diagnosis_id and a trajectory_id"
            )
        if lesson.diagnosis_id not in self._diagnoses:
            raise MissingEvidenceLink(
                f"lesson {lesson.lesson_id} links to unknown diagnosis {lesson.diagnosis_id}"
            )
        if lesson.trajectory_id not in self._trajectories:
            raise MissingEvidenceLink(
                f"lesson {lesson.lesson_id} links to unknown trajectory {lesson.trajectory_id}"
            )
        self._lessons[lesson.lesson_id] = lesson

    # -- reads -------------------------------------------------------------

    def lesson(self, lesson_id: str) -> Lesson:
        return self._lessons[lesson_id]

    def trajectory(self, trajectory_id: str) -> Trajectory:
        return self._trajectories[trajectory_id]

    def diagnosis(self, diagnosis_id: str) -> Diagnosis:
        return self._diagnoses[diagnosis_id]

    def trajectory_for_lesson(self, lesson_id: str) -> Trajectory:
        return self._trajectories[self._lessons[lesson_id].trajectory_id]

    def diagnosis_for_lesson(self, lesson_id: str) -> Diagnosis:
        return self._diagnoses[self._lessons[lesson_id].diagnosis_id]

    def lessons_for(self, context_key: str) -> list[Lesson]:
        """All lessons for a context, in insertion order."""
        return [l for l in self._lessons.values() if l.context_key == context_key]

    def all_lessons(self) -> list[Lesson]:
        return list(self._lessons.values())

    def __len__(self) -> int:
        return len(self._lessons)
