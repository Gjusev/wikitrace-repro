"""Link-walking pre-action check.

Before acting on a lesson, walk its evidence links (lesson -> diagnosis ->
raw trajectory) and decide: act, act with a corrected/recovered action, or
refuse the lesson. This is the offline, deterministic analogue of
WikiTrace's descent through the read-only corpus with terminal tools.
"""

from __future__ import annotations

from dataclasses import dataclass

from .detector import detect
from .store import Lesson, LessonStore


@dataclass(frozen=True)
class Verdict:
    lesson_id: str
    action: str  # what the agent should do
    acted_on_lesson: bool
    walked_links: bool
    reason: str


class LinkWalker:
    """Deterministic link walker over a :class:`LessonStore`."""

    def __init__(self, store: LessonStore) -> None:
        self.store = store

    def pre_action_check(self, lesson: Lesson) -> Verdict:
        trajectory = self.store.trajectory_for_lesson(lesson.lesson_id)
        flags = detect(self.store, lesson)

        # 1. Failure-sourced: the diagnosis/trajectory show it did not work.
        if flags.failure_sourced:
            return Verdict(
                lesson_id=lesson.lesson_id,
                action="",
                acted_on_lesson=False,
                walked_links=True,
                reason="refused: lesson comes from a failed run "
                f"(diagnosis/trajectory of {trajectory.run_id} show it did not work)",
            )

        # 2. Conflicting: resolve via the successful source trajectories.
        if flags.conflicting_with:
            candidates = [lesson] + [
                self.store.lesson(peer_id) for peer_id in flags.conflicting_with
            ]
            confirmed = [
                cand
                for cand in candidates
                if self.store.trajectory_for_lesson(cand.lesson_id).success
            ]
            confirmed_actions = {cand.action for cand in confirmed}
            if len(confirmed_actions) == 1:
                action = confirmed_actions.pop()
                return Verdict(
                    lesson_id=lesson.lesson_id,
                    action=action,
                    acted_on_lesson=True,
                    walked_links=True,
                    reason=f"conflict resolved via successful source trajectories -> {action}",
                )
            return Verdict(
                lesson_id=lesson.lesson_id,
                action="",
                acted_on_lesson=False,
                walked_links=True,
                reason="refused: conflict could not be resolved from source trajectories",
            )

        # 3. Incomplete: recover the missing detail from the raw trajectory.
        if flags.incomplete:
            if trajectory.success:
                return Verdict(
                    lesson_id=lesson.lesson_id,
                    action=trajectory.final_action,
                    acted_on_lesson=True,
                    walked_links=True,
                    reason="missing detail recovered from raw trajectory "
                    f"({trajectory.run_id}) -> {trajectory.final_action}",
                )
            return Verdict(
                lesson_id=lesson.lesson_id,
                action="",
                acted_on_lesson=False,
                walked_links=True,
                reason="refused: lesson incomplete and its source run failed",
            )

        # 4. Clean: complete, unchallenged, success-sourced.
        return Verdict(
            lesson_id=lesson.lesson_id,
            action=lesson.action,
            acted_on_lesson=True,
            walked_links=False,
            reason="lesson is complete, unchallenged and success-sourced",
        )
