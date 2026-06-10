"""Mechanical, text-derived metrics.

These are cheap signals computed without the LLM. For text takes we can only
get text-shape metrics (word count, fillers, sentence length). Timing-derived
metrics (WPM, pauses) need audio + whisper timestamps and arrive with the
audio path later.
"""
from __future__ import annotations

import re
from typing import Any, Dict

# Common verbal fillers (English). Cantonese fillers can be added later.
FILLERS = [
    "um", "uh", "erm", "ah", "like", "you know", "i mean", "sort of",
    "kind of", "basically", "actually", "literally", "right", "so yeah",
]


def text_metrics(text: str) -> Dict[str, Any]:
    words = re.findall(r"\b[\w']+\b", text.lower())
    word_count = len(words)

    lower = text.lower()
    filler_count = 0
    for f in FILLERS:
        filler_count += len(re.findall(r"\b" + re.escape(f) + r"\b", lower))

    sentences = [s for s in re.split(r"[.!?]+", text) if s.strip()]
    sentence_count = len(sentences)
    avg_sentence_len = round(word_count / sentence_count, 1) if sentence_count else 0.0

    return {
        "word_count": word_count,
        "sentence_count": sentence_count,
        "avg_sentence_len": avg_sentence_len,
        "filler_count": filler_count,
        "filler_rate": round(filler_count / word_count, 3) if word_count else 0.0,
        # Timing metrics are unavailable for text; null until audio lands.
        "wpm": None,
        "duration_sec": None,
        "pause_p50": None,
        "pause_p90": None,
    }
