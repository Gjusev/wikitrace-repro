"""Deterministic stub agent for offline harness validation.

This is a scripted rule agent, NOT an LLM. It exists so the full loop --
memory retrieval, degradation detection, link walking, action, scoring --
can be exercised offline with zero cost. Three memory modes mirror the
official WikiTrace harness's methods: no-memory, insights-only (blind),
and wikitrace (evidence-checked).
"""

from __future__ import annotations

from dataclasses import dataclass

from .detector import detect
from .store import LessonStore
from .walker import LinkWalker

MODE_NO_MEMORY = "no-memory"
MODE_INSIGHTS_ONLY = "insights-only"
MODE_WIKITRACE = "wikitrace"
MODES = (MODE_NO_MEMORY, MODE_INSIGHTS_ONLY, MODE_WIKITRACE)


@dataclass(frozen=True)
class Task:
    task_id: str
    context_key: str
    ground_truth_action: str


@dataclass(frozen=True)
class Step:
    task_id: str
    context_key: str
    action: str
    success: bool
    acted_on_lesson: bool
    wrong_lesson_followed: bool
    walked_links: bool
    reason: str


class StubAgent:
    """Rule-based agent. ``default_actions`` is what it does without memory."""

    def __init__(
        self,
        store: LessonStore,
        mode: str,
        default_actions: dict[str, str],
    ) -> None:
        if mode not in MODES:
            raise ValueError(f"unknown mode: {mode!r}; expected one of {MODES}")
        self.store = store
        self.mode = mode
        self.default_actions = default_actions
        self.walker = LinkWalker(store)

    def solve(self, task: Task) -> Step:
        lessons = self.store.lessons_for(task.context_key)
        if self.mode == MODE_NO_MEMORY or not lessons:
            action = self.default_actions[task.context_key]
            return self._score(task, action, acted_on_lesson=False, walked=False,
                               reason="no memory: default action")

        if self.mode == MODE_INSIGHTS_ONLY:
            # Blind: trusts the first matching insight verbatim, no link walk.
            lesson = lessons[0]
            return self._score(task, lesson.action, acted_on_lesson=True, walked=False,
                               reason=f"followed lesson {lesson.lesson_id} verbatim")

        # wikitrace mode: check every lesson against its evidence links first.
        clean = [l for l in lessons if not detect(self.store, l).flagged]
        flagged = [l for l in lessons if detect(self.store, l).flagged]
        for lesson in clean:
            return self._score(task, lesson.action, acted_on_lesson=True, walked=False,
                               reason=f"followed verified lesson {lesson.lesson_id}")
        for lesson in flagged:
            verdict = self.walker.pre_action_check(lesson)
            if verdict.acted_on_lesson and verdict.action:
                return self._score(task, verdict.action, acted_on_lesson=True, walked=True,
                                   reason=verdict.reason)
        return self._score(task, self.default_actions[task.context_key],
                           acted_on_lesson=False, walked=True,
                           reason="all lessons refused after link walk: default action")

    def _score(self, task: Task, action: str, *, acted_on_lesson: bool,
               walked: bool, reason: str) -> Step:
        success = action == task.ground_truth_action
        return Step(
            task_id=task.task_id,
            context_key=task.context_key,
            action=action,
            success=success,
            acted_on_lesson=acted_on_lesson,
            wrong_lesson_followed=acted_on_lesson and not success,
            walked_links=walked,
            reason=reason,
        )
