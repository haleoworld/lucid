"""The per-take processing pipeline.

  text take:  source_text -> metrics -> coaching report
  audio take: audio -> transcribe (local whisper) -> metrics -> coaching report

Mirrors elevator's _run_pipeline, stripped of interview-specific stages
(diarization, interview question-matching).
"""
from __future__ import annotations

from . import coaching, config, db, metrics, notify, transcribe


def _take_url(take_id: int) -> str:
    base = config.PUBLIC_URL.rstrip("/") if config.PUBLIC_URL else ""
    return f"{base}{config.URL_PREFIX}/take/{take_id}" if base else ""


def run(take_id: int) -> None:
    take = db.get_take(take_id)
    if not take:
        return
    db.set_take_status(take_id, "processing")
    try:
        if take["kind"] == "audio":
            if not transcribe.is_available():
                raise RuntimeError(
                    "mlx-whisper is not installed; cannot transcribe audio yet."
                )
            text, segments = transcribe.transcribe(take["audio_path"])
        else:
            text = take["source_text"]
            segments = []

        if not text.strip():
            raise RuntimeError("Nothing to analyze (empty transcript).")

        m = metrics.text_metrics(text)
        db.save_transcript(take_id, text, segments, m)

        mini = db.get_mini_project(take["mini_project_id"]) or {}
        project = db.get_project(mini.get("project_id", 0)) or {}

        report = coaching.synthesize(
            text, m,
            title=mini.get("title", ""),
            domain=mini.get("domain", "learning"),
            situation=mini.get("situation", ""),
            project_goal=project.get("goal", ""),
            project_tone=project.get("tone", ""),
            mini_goal=mini.get("goal", ""),
            mini_tone=mini.get("tone", ""),
            intended_message=take["intended_message"],
            language=take["language"],
        )
        db.save_report(take_id, report)
        db.set_take_status(take_id, "done")
        heard = report.get("heard_message", "")
        notify.send(f"✅ Lucid · take #{take_id} report ready\nHeard: {heard}\n{_take_url(take_id)}".strip())
    except Exception as exc:  # noqa: BLE001
        db.set_take_status(take_id, "failed", str(exc))
        notify.send(f"❌ Lucid · take #{take_id} failed: {exc}\n{_take_url(take_id)}".strip())
