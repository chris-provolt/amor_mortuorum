from __future__ import annotations

import json
import os
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
import threading
import uuid


@dataclass
class TelemetryEvent:
    """Schema for telemetry events written as JSON-Lines."""
    event: str
    ts: str
    attrs: Dict[str, Any]
    session: str
    seq: int


class TelemetryClient:
    """
    Lightweight telemetry client that writes JSON-Lines events to disk.

    - Safe to use without network.
    - Flushes on buffer size; can be flushed manually.
    - Disabled state is a no-op.
    """

    def __init__(
        self,
        enabled: bool = True,
        out_dir: Optional[Path] = None,
        app_name: str = "Amor Mortuorum",
        build_version: str = "dev",
        flush_size: int = 50,
    ) -> None:
        self.enabled = enabled
        self._lock = threading.RLock()
        self._buffer: List[TelemetryEvent] = []
        self._seq = 0
        self._global_context: Dict[str, Any] = {
            "app": app_name,
            "build": build_version,
            "pid": os.getpid(),
        }
        self._session = str(uuid.uuid4())
        self._flush_size = max(1, flush_size)
        self._dir = Path(out_dir or (Path.home() / ".amor" / "telemetry"))
        self._dir.mkdir(parents=True, exist_ok=True)
        ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        self._file = self._dir / f"session-{ts}-{self._session[:8]}.log"

    @property
    def output_file(self) -> Path:
        return self._file

    def set_global_context(self, **kwargs: Any) -> None:
        with self._lock:
            self._global_context.update(kwargs)

    def emit(self, event: str, **attrs: Any) -> None:
        if not self.enabled:
            return
        with self._lock:
            self._seq += 1
            payload = dict(self._global_context)
            payload.update(attrs)
            ev = TelemetryEvent(
                event=event,
                ts=datetime.now(timezone.utc).isoformat(),
                attrs=payload,
                session=self._session,
                seq=self._seq,
            )
            self._buffer.append(ev)
            if len(self._buffer) >= self._flush_size:
                self.flush()

    def flush(self, force: bool = True) -> None:
        if not self.enabled:
            return
        with self._lock:
            if not self._buffer:
                return
            # Write atomically: open append and write all lines
            with self._file.open("a", encoding="utf-8") as f:
                for ev in self._buffer:
                    f.write(json.dumps(asdict(ev), ensure_ascii=False) + "\n")
                f.flush()
            self._buffer.clear()

    def close(self) -> None:
        self.flush(force=True)

    def __enter__(self) -> "TelemetryClient":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()
