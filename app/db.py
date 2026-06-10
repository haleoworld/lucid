"""SQLite storage.

Schema mirrors the elevator project's idea — one transcript/report schema that
attaches to a "subject" — but the subject here is a *take* (one recorded or
written attempt at articulating an idea) under a mini-project under a project.

  project (global goal + tone)
    └─ mini_project (its own goal + tone)
         └─ take (one attempt; text now, audio later)
              ├─ transcript
              └─ coaching_report
"""
from __future__ import annotations

import json
import sqlite3
import time
from typing import Any, Dict, List, Optional

from . import config


def _conn() -> sqlite3.Connection:
    config.ensure_dirs()
    conn = sqlite3.connect(config.DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


SCHEMA = """
CREATE TABLE IF NOT EXISTS projects (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT NOT NULL,
    goal        TEXT NOT NULL DEFAULT '',
    tone        TEXT NOT NULL DEFAULT '',
    created_at  REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS mini_projects (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id  INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    title       TEXT NOT NULL,
    goal        TEXT NOT NULL DEFAULT '',
    tone        TEXT NOT NULL DEFAULT '',
    status      TEXT NOT NULL DEFAULT 'active',
    created_at  REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS takes (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    mini_project_id  INTEGER NOT NULL REFERENCES mini_projects(id) ON DELETE CASCADE,
    kind             TEXT NOT NULL DEFAULT 'text',   -- 'text' | 'audio'
    language         TEXT NOT NULL DEFAULT 'english',
    intended_message TEXT NOT NULL DEFAULT '',       -- what you MEANT to land
    source_text      TEXT NOT NULL DEFAULT '',       -- pasted text (text kind)
    audio_path       TEXT NOT NULL DEFAULT '',       -- audio kind (later)
    status           TEXT NOT NULL DEFAULT 'queued', -- queued|processing|done|failed
    error            TEXT NOT NULL DEFAULT '',
    created_at       REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS transcripts (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    take_id     INTEGER NOT NULL REFERENCES takes(id) ON DELETE CASCADE,
    text        TEXT NOT NULL,
    segments_json TEXT NOT NULL DEFAULT '[]',
    metrics_json  TEXT NOT NULL DEFAULT '{}',
    created_at  REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS coaching_reports (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    take_id     INTEGER NOT NULL REFERENCES takes(id) ON DELETE CASCADE,
    report_json TEXT NOT NULL,
    created_at  REAL NOT NULL
);
"""


def init_db() -> None:
    conn = _conn()
    try:
        conn.executescript(SCHEMA)
        conn.commit()
        # Seed a default global project if none exists.
        row = conn.execute("SELECT COUNT(*) AS n FROM projects").fetchone()
        if row["n"] == 0:
            conn.execute(
                "INSERT INTO projects (name, goal, tone, created_at) VALUES (?,?,?,?)",
                (
                    "Communication & interpersonal skills",
                    "Close the gap between what I achieve and what others understand — "
                    "communicate with clear structure so people stay in sync.",
                    "Clear, structured, lead-with-the-message. Concise over rambly.",
                    time.time(),
                ),
            )
            conn.commit()
    finally:
        conn.close()


# --- projects ---------------------------------------------------------------

def list_projects() -> List[Dict[str, Any]]:
    conn = _conn()
    try:
        return [dict(r) for r in conn.execute(
            "SELECT * FROM projects ORDER BY id"
        ).fetchall()]
    finally:
        conn.close()


def get_project(pid: int) -> Optional[Dict[str, Any]]:
    conn = _conn()
    try:
        r = conn.execute("SELECT * FROM projects WHERE id=?", (pid,)).fetchone()
        return dict(r) if r else None
    finally:
        conn.close()


# --- mini projects ----------------------------------------------------------

def create_mini_project(project_id: int, title: str, goal: str, tone: str) -> int:
    conn = _conn()
    try:
        cur = conn.execute(
            "INSERT INTO mini_projects (project_id, title, goal, tone, created_at) "
            "VALUES (?,?,?,?,?)",
            (project_id, title, goal, tone, time.time()),
        )
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def list_mini_projects(project_id: int) -> List[Dict[str, Any]]:
    conn = _conn()
    try:
        rows = conn.execute(
            "SELECT m.*, "
            "(SELECT COUNT(*) FROM takes t WHERE t.mini_project_id=m.id) AS take_count "
            "FROM mini_projects m WHERE m.project_id=? ORDER BY m.id DESC",
            (project_id,),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def get_mini_project(mid: int) -> Optional[Dict[str, Any]]:
    conn = _conn()
    try:
        r = conn.execute("SELECT * FROM mini_projects WHERE id=?", (mid,)).fetchone()
        return dict(r) if r else None
    finally:
        conn.close()


# --- takes ------------------------------------------------------------------

def create_take(mini_project_id: int, kind: str, language: str,
                intended_message: str, source_text: str = "",
                audio_path: str = "") -> int:
    conn = _conn()
    try:
        cur = conn.execute(
            "INSERT INTO takes (mini_project_id, kind, language, intended_message, "
            "source_text, audio_path, status, created_at) VALUES (?,?,?,?,?,?,?,?)",
            (mini_project_id, kind, language, intended_message, source_text,
             audio_path, "queued", time.time()),
        )
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def get_take(take_id: int) -> Optional[Dict[str, Any]]:
    conn = _conn()
    try:
        r = conn.execute("SELECT * FROM takes WHERE id=?", (take_id,)).fetchone()
        return dict(r) if r else None
    finally:
        conn.close()


def list_takes(mini_project_id: int) -> List[Dict[str, Any]]:
    conn = _conn()
    try:
        rows = conn.execute(
            "SELECT * FROM takes WHERE mini_project_id=? ORDER BY id DESC",
            (mini_project_id,),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def set_take_status(take_id: int, status: str, error: str = "") -> None:
    conn = _conn()
    try:
        conn.execute("UPDATE takes SET status=?, error=? WHERE id=?",
                     (status, error, take_id))
        conn.commit()
    finally:
        conn.close()


def takes_needing_processing() -> List[int]:
    conn = _conn()
    try:
        rows = conn.execute(
            "SELECT id FROM takes WHERE status IN ('queued','processing')"
        ).fetchall()
        return [r["id"] for r in rows]
    finally:
        conn.close()


# --- transcripts & reports --------------------------------------------------

def save_transcript(take_id: int, text: str, segments: List[Any],
                    metrics: Dict[str, Any]) -> None:
    conn = _conn()
    try:
        conn.execute("DELETE FROM transcripts WHERE take_id=?", (take_id,))
        conn.execute(
            "INSERT INTO transcripts (take_id, text, segments_json, metrics_json, created_at) "
            "VALUES (?,?,?,?,?)",
            (take_id, text, json.dumps(segments), json.dumps(metrics), time.time()),
        )
        conn.commit()
    finally:
        conn.close()


def get_transcript(take_id: int) -> Optional[Dict[str, Any]]:
    conn = _conn()
    try:
        r = conn.execute("SELECT * FROM transcripts WHERE take_id=?",
                         (take_id,)).fetchone()
        if not r:
            return None
        d = dict(r)
        d["segments"] = json.loads(d.pop("segments_json") or "[]")
        d["metrics"] = json.loads(d.pop("metrics_json") or "{}")
        return d
    finally:
        conn.close()


def save_report(take_id: int, report: Dict[str, Any]) -> None:
    conn = _conn()
    try:
        conn.execute("DELETE FROM coaching_reports WHERE take_id=?", (take_id,))
        conn.execute(
            "INSERT INTO coaching_reports (take_id, report_json, created_at) "
            "VALUES (?,?,?)",
            (take_id, json.dumps(report), time.time()),
        )
        conn.commit()
    finally:
        conn.close()


def get_report(take_id: int) -> Optional[Dict[str, Any]]:
    conn = _conn()
    try:
        r = conn.execute("SELECT * FROM coaching_reports WHERE take_id=?",
                         (take_id,)).fetchone()
        if not r:
            return None
        return json.loads(r["report_json"])
    finally:
        conn.close()
