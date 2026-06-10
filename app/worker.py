"""A single background worker draining a queue one job at a time.

Serialized on purpose (like elevator): avoids DB contention and, later, keeps
only one whisper transcription running at once on the Mac mini.
"""
from __future__ import annotations

import queue
import threading

from . import db, pipeline

_q: "queue.Queue[int]" = queue.Queue()
_started = False
_lock = threading.Lock()


def _loop() -> None:
    while True:
        take_id = _q.get()
        try:
            pipeline.run(take_id)
        except Exception:  # noqa: BLE001 — never let the worker die
            pass
        finally:
            _q.task_done()


def start() -> None:
    """Start the worker thread and re-queue any unfinished takes (auto-resume)."""
    global _started
    with _lock:
        if _started:
            return
        t = threading.Thread(target=_loop, daemon=True, name="take-worker")
        t.start()
        _started = True
    for take_id in db.takes_needing_processing():
        _q.put(take_id)


def enqueue(take_id: int) -> None:
    _q.put(take_id)
