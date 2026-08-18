"""Bounded workers. No unbounded thread explosion. Graceful shutdown."""
from __future__ import annotations

import queue
import threading
from typing import Any, Callable

from .config import FailClosed

MAX_QUEUE = 32
MAX_WORKERS = 4


class BoundedWorker:
    def __init__(self, name: str, handler: Callable[[Any], Any], maxsize: int = MAX_QUEUE) -> None:
        self.name = name
        self.handler = handler
        self.queue: queue.Queue[Any] = queue.Queue(maxsize=maxsize)
        self._stop = threading.Event()
        self.thread = threading.Thread(target=self._loop, name=name, daemon=True)
        self.errors: list[str] = []

    def start(self) -> None:
        self.thread.start()

    def submit(self, item: Any) -> None:
        try:
            self.queue.put_nowait(item)
        except queue.Full as exc:
            raise FailClosed(f"WORKER_QUEUE_FULL:{self.name}") from exc

    def _loop(self) -> None:
        while not self._stop.is_set():
            try:
                item = self.queue.get(timeout=0.05)
            except queue.Empty:
                continue
            try:
                self.handler(item)
            except Exception as exc:  # noqa: BLE001 — worker must not die silently without record
                self.errors.append(f"{type(exc).__name__}:{exc}")
            finally:
                self.queue.task_done()

    def shutdown(self) -> None:
        self._stop.set()
        if self.thread.ident is not None:
            self.thread.join(timeout=2.0)


class WorkerPool:
    def __init__(self, handlers: dict[str, Callable[[Any], Any]]) -> None:
        if len(handlers) > MAX_WORKERS + 4:
            raise FailClosed("UNCONTROLLED_THREAD_EXPLOSION")
        names = (
            "ExperienceWorker",
            "ReplayWorker",
            "CuriosityWorker",
            "CurriculumWorker",
            "TeacherMiningWorker",
            "BenchmarkWorker",
            "SkillCompilerWorker",
            "MaintenanceWorker",
        )
        self.workers = {n: BoundedWorker(n, handlers.get(n, lambda _x: None)) for n in names}

    def start(self) -> None:
        for w in self.workers.values():
            w.start()

    def shutdown(self) -> None:
        for w in self.workers.values():
            w.shutdown()
