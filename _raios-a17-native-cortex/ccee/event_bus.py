"""In-process cognitive event bus. Shared state, no uncontrolled mutation."""
from __future__ import annotations

import threading
from collections import defaultdict
from typing import Any, Callable

from .wal import CognitiveWAL

Handler = Callable[[dict[str, Any]], None]


class EventBus:
    def __init__(self, wal: CognitiveWAL) -> None:
        self.wal = wal
        self._handlers: dict[str, list[Handler]] = defaultdict(list)
        self._lock = threading.RLock()

    def subscribe(self, event_type: str, handler: Handler) -> None:
        with self._lock:
            self._handlers[event_type].append(handler)

    def emit(self, event_type: str, source: str, payload: dict[str, Any], **kwargs: Any) -> Any:
        event = self.wal.append(event_type, source, payload, **kwargs)
        with self._lock:
            handlers = list(self._handlers.get(event_type, ())) + list(self._handlers.get("*", ()))
        for handler in handlers:
            handler(event.model_dump())
        return event
