"""Degradation detector: flags lessons an agent must not trust blindly.

Three conditions, from the paper (arXiv:2611.14320): the lesson lacks
details needed to act (incomplete), conflicts with another lesson, or
comes from a failed run (failure-sourced). These are exactly the triggers
that make WikiTrace's agent descend through its evidence links.
"""

from __future__ import annotations

from dataclasses import dataclass

from .store import Lesson, LessonStore

#: Substrings that mark a lesson as having lost the details needed to act.
#: ``<``/``...`` catch elided parameters ("systemctl restart <service>"),
#: ``TODO``/``TBD`` catch unwritten lessons.
INCOMPLETE_MARKERS = ("<", "...", "TODO", "TBD")


@dataclass(frozen=True)
class Flags:
    lesson_id: str
    incomplete: bool
    conflicting_with: tuple[str, ...]
    failure_sourced: bool

    @property
    def flagged(self) -> bool:
        return bool(self.incomplete or self.conflicting_with or self.failure_sourced)

    def summary(self) -> str:
        parts = []
        if self.incomplete:
            parts.append("incomplete")
        if self.conflicting_with:
            parts.append("conflicts:" + ",".join(self.conflicting_with))
        if self.failure_sourced:
            parts.append("failure-sourced")
        return ";".join(parts) if parts else "clean"


def is_incomplete(text: str) -> bool:
    return any(marker in text or marker in text.lower() for marker in INCOMPLETE_MARKERS)


def detect(store: LessonStore, lesson: Lesson) -> Flags:
    """Flag one lesson against the rest of the store.

    The lesson itself is EXCLUDED from its own comparison set: a freshly
    added lesson must not conflict with itself.
    """
    peers = [
        other
        for other in store.lessons_for(lesson.context_key)
        if other.lesson_id != lesson.lesson_id
    ]
    conflicting = tuple(other.lesson_id for other in peers if other.action != lesson.action)

    diagnosis = store.diagnosis_for_lesson(lesson.lesson_id)
    trajectory = store.trajectory_for_lesson(lesson.lesson_id)
    failure_sourced = diagnosis.outcome == "failure" or not trajectory.success

    return Flags(
        lesson_id=lesson.lesson_id,
        incomplete=is_incomplete(lesson.text) or is_incomplete(lesson.action),
        conflicting_with=conflicting,
        failure_sourced=failure_sourced,
    )
