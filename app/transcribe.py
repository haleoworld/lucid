"""Audio transcription via local mlx-whisper (Apple Silicon).

Kept isolated and lazy-imported so the app runs fine for the text-paste path
even when mlx-whisper isn't installed yet. Audio stays on this machine.
"""
from __future__ import annotations

from typing import Any, Dict, List, Tuple

MODEL = "mlx-community/whisper-medium-mlx"


def is_available() -> bool:
    try:
        import mlx_whisper  # noqa: F401
        return True
    except Exception:
        return False


def transcribe(audio_path: str) -> Tuple[str, List[Dict[str, Any]]]:
    """Return (full_text, segments[{start, end, text}]). Requires mlx-whisper."""
    import mlx_whisper  # type: ignore

    result = mlx_whisper.transcribe(audio_path, path_or_hf_repo=MODEL)
    text = (result.get("text") or "").strip()
    segments = [
        {"start": s.get("start"), "end": s.get("end"), "text": (s.get("text") or "").strip()}
        for s in result.get("segments", [])
    ]
    return text, segments
