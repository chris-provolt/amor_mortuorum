from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class ToastMessage:
    """A non-blocking UI notification message.

    This model is UI-framework agnostic; the actual rendering layer can poll
    the ToastManager for messages to display on screen.
    """

    text: str
    level: str = "info"  # info | warning | error | success
    duration: float = 2.5  # seconds to display (advisory; renderer decides)
    timestamp: float = field(default_factory=lambda: time.time())


class ToastManager:
    """Thread-safe manager for non-blocking UI toasts.

    In the live game, the UI layer should regularly drain() the queue and
    render messages on screen. For tests, you can inspect the queue or the
    last_message property to assert behavior.
    """

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._queue: List[ToastMessage] = []
        self._last: Optional[ToastMessage] = None

    def show(self, text: str, level: str = "info", duration: float = 2.5) -> None:
        msg = ToastMessage(text=text, level=level, duration=duration)
        with self._lock:
            self._queue.append(msg)
            self._last = msg

    def drain(self) -> List[ToastMessage]:
        with self._lock:
            items = list(self._queue)
            self._queue.clear()
            return items

    @property
    def has_pending(self) -> bool:
        with self._lock:
            return bool(self._queue)

    @property
    def last_message(self) -> Optional[ToastMessage]:
        with self._lock:
            return self._last
