"""Offline synthetic degradation bench.

HARNESS VALIDATION ONLY: a deterministic stub agent on synthetic tasks.
This demonstrates the *mechanism direction* (evidence-linked memory reduces
memory-induced degradation vs. the same insights without links) on stub
data. It is NOT a reproduction of the paper's benchmark numbers.
"""

from __future__ import annotations

from dataclasses import dataclass

from .agent import MODES, MODE_INSIGHTS_ONLY, MODE_NO_MEMORY, MODE_WIKITRACE, StubAgent, Task
from .store import Diagnosis, Lesson, LessonStore, Trajectory

# -- synthetic task set (8 tasks, 5 with memory coverage) --------------------

TASKS: tuple[Task, ...] = (
    Task("deploy-api", "deploy", "deploy api --canary"),
    Task("restart-postgres", "restart", "systemctl restart postgresql"),
    Task("backup-db", "backup", "pg_dump prod > backup.sql"),
    Task("flush-cache", "cache", "redis-cli FLUSHALL"),
    Task("migrate-db", "migrate", "alembic upgrade head"),
    Task("tail-logs", "logs", "journalctl -f -u api"),
    Task("scale-web", "scale", "scale web --replicas 4"),
    Task("rollback-release", "rollback", "release rollback --to previous"),
)

DEFAULT_ACTIONS = {t.context_key: t.ground_truth_action for t in TASKS}


def build_corpus() -> LessonStore:
    """Synthetic training runs -> a small evidence-linked corpus.

    Deliberately contains the three degradation triggers from the paper:
    an incomplete lesson (parameter elided), a failure-sourced wrong lesson,
    and a pair of conflicting lessons.
    """
    store = LessonStore()

    # deploy: clean, correct, success-sourced.
    store.add_trajectory(Trajectory(
        "run-deploy-ok", "deploy api to staging",
        ("git pull", "deploy api --canary", "health check ok"),
        final_action="deploy api --canary", success=True))
    store.add_diagnosis(Diagnosis(
        "diag-deploy-ok", "run-deploy-ok", outcome="success",
        cause="canary deploy verified healthy"))
    store.add_lesson(Lesson(
        "deploy-ok", "For deploy tasks run deploy api --canary.",
        context_key="deploy", action="deploy api --canary",
        diagnosis_id="diag-deploy-ok", trajectory_id="run-deploy-ok"))

    # restart: successful run, but the compiled lesson LOST the parameter.
    store.add_trajectory(Trajectory(
        "run-restart-ok", "restart postgres",
        ("systemctl restart postgresql", "port 5432 accepting connections"),
        final_action="systemctl restart postgresql", success=True))
    store.add_diagnosis(Diagnosis(
        "diag-restart-ok", "run-restart-ok", outcome="success",
        cause="service restarted cleanly"))
    store.add_lesson(Lesson(
        "restart-elided", "For restart tasks run systemctl restart <service>.",
        context_key="restart", action="systemctl restart <service>",
        diagnosis_id="diag-restart-ok", trajectory_id="run-restart-ok"))

    # cache: a failed run; the lesson records the command that FAILED.
    store.add_trajectory(Trajectory(
        "run-cache-fail", "flush cache",
        ("redis-cli FLUSHDB", "session store wiped, users logged out"),
        final_action="redis-cli FLUSHDB", success=False))
    store.add_diagnosis(Diagnosis(
        "diag-cache-fail", "run-cache-fail", outcome="failure",
        cause="FLUSHDB hit the wrong db scope and killed sessions"))
    store.add_lesson(Lesson(
        "cache-naive", "For cache flush tasks run redis-cli FLUSHDB.",
        context_key="cache", action="redis-cli FLUSHDB",
        diagnosis_id="diag-cache-fail", trajectory_id="run-cache-fail"))

    # migrate: conflicting pair -- the WRONG lesson is inserted first so a
    # blind agent that trusts "the first matching lesson" picks it.
    store.add_trajectory(Trajectory(
        "run-migrate-fail", "migrate db",
        ("alembic downgrade base", "schema dropped, data lost"),
        final_action="alembic downgrade base", success=False))
    store.add_diagnosis(Diagnosis(
        "diag-migrate-fail", "run-migrate-fail", outcome="failure",
        cause="downgrade destroyed the schema; needed upgrade, not downgrade"))
    store.add_lesson(Lesson(
        "migrate-wrong", "For migrate tasks run alembic downgrade base.",
        context_key="migrate", action="alembic downgrade base",
        diagnosis_id="diag-migrate-fail", trajectory_id="run-migrate-fail"))
    store.add_trajectory(Trajectory(
        "run-migrate-ok", "migrate db correctly",
        ("alembic upgrade head", "schema at head"),
        final_action="alembic upgrade head", success=True))
    store.add_diagnosis(Diagnosis(
        "diag-migrate-ok", "run-migrate-ok", outcome="success",
        cause="upgrade applied cleanly"))
    store.add_lesson(Lesson(
        "migrate-right", "For migrate tasks run alembic upgrade head.",
        context_key="migrate", action="alembic upgrade head",
        diagnosis_id="diag-migrate-ok", trajectory_id="run-migrate-ok"))

    # scale: incomplete AND failure-sourced.
    store.add_trajectory(Trajectory(
        "run-scale-fail", "scale web tier",
        ("scale web --replicas 4", "autoscaler rejected the change"),
        final_action="scale web --replicas 4", success=False))
    store.add_diagnosis(Diagnosis(
        "diag-scale-fail", "run-scale-fail", outcome="failure",
        cause="autoscaler config missing; replica change rejected"))
    store.add_lesson(Lesson(
        "scale-vague", "For scale tasks run scale web --replicas <n>.",
        context_key="scale", action="scale web --replicas <n>",
        diagnosis_id="diag-scale-fail", trajectory_id="run-scale-fail"))

    return store


# -- metrics -----------------------------------------------------------------


@dataclass(frozen=True)
class ModeResult:
    mode: str
    tasks: int
    successes: int
    wrong_lesson_followed: int
    degradation: int  # tasks no-memory solves that this mode fails

    @property
    def success_rate(self) -> float:
        return self.successes / self.tasks

    @property
    def wrong_lesson_rate(self) -> float:
        return self.wrong_lesson_followed / self.tasks

    @property
    def degradation_rate(self) -> float:
        return self.degradation / self.tasks


def run_mode(mode: str) -> ModeResult:
    store = build_corpus()
    agent = StubAgent(store, mode, DEFAULT_ACTIONS)
    steps = [agent.solve(task) for task in TASKS]
    no_memory_successes = len(TASKS)  # the stub agent solves every task without memory
    successes = sum(1 for s in steps if s.success)
    wrong = sum(1 for s in steps if s.wrong_lesson_followed)
    degradation = no_memory_successes - successes
    return ModeResult(mode=mode, tasks=len(TASKS), successes=successes,
                      wrong_lesson_followed=wrong, degradation=degradation)


def run_bench() -> str:
    """Run all three modes; return a human-readable report."""
    results = [run_mode(mode) for mode in MODES]
    by_mode = {r.mode: r for r in results}
    lines = [
        "HARNESS VALIDATION -- offline stub bench (deterministic rule agent,",
        "synthetic tasks). This is NOT a reproduction of the paper's benchmark",
        "numbers; it validates that the evidence-chain mechanism works offline.",
        "",
        "Memory-induced degradation = tasks the no-memory agent solves but the",
        "memory mode fails.",
        "",
        f"{'mode':<16}{'success':>10}{'wrong-lesson':>15}{'degradation':>14}",
        "-" * 55,
    ]
    for r in results:
        lines.append(
            f"{r.mode:<16}{f'{r.successes}/{r.tasks}':>10}"
            f"{f'{r.wrong_lesson_followed}/{r.tasks}':>15}"
            f"{f'{r.degradation}/{r.tasks}':>14}"
        )
    lines += [
        "",
        "Mechanism check:",
        f"  degradation, insights-only vs wikitrace: "
        f"{by_mode[MODE_INSIGHTS_ONLY].degradation} -> {by_mode[MODE_WIKITRACE].degradation}",
        f"  wrong-lesson rate, insights-only vs wikitrace: "
        f"{by_mode[MODE_INSIGHTS_ONLY].wrong_lesson_rate:.1%} -> "
        f"{by_mode[MODE_WIKITRACE].wrong_lesson_rate:.1%}",
    ]
    return "\n".join(lines)
