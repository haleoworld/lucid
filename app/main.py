"""FastAPI app: web UI + routes for mini-projects and takes."""
from __future__ import annotations

import time
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, Form, Request, UploadFile, File
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from . import config, db, worker

BASE = Path(__file__).resolve().parent
templates = Jinja2Templates(directory=str(BASE / "templates"))

app = FastAPI(title="Lucid")
app.mount("/static", StaticFiles(directory=str(BASE / "static")), name="static")


@app.on_event("startup")
def _startup() -> None:
    config.ensure_dirs()
    db.init_db()
    worker.start()


# --- helpers ----------------------------------------------------------------

def _current_project() -> dict:
    projects = db.list_projects()
    return projects[0]  # single global project for now


def render(request: Request, name: str, **ctx):
    """Render a template, always injecting request + URL prefix."""
    ctx["request"] = request
    ctx["prefix"] = config.URL_PREFIX
    return templates.TemplateResponse(name, ctx)


def redirect(path: str) -> RedirectResponse:
    """303 redirect to an app path, prefixed for the subpath mount."""
    return RedirectResponse(config.URL_PREFIX + path, status_code=303)


# --- pages ------------------------------------------------------------------

@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    project = _current_project()
    minis = db.list_mini_projects(project["id"])
    return render(request, "index.html", project=project, minis=minis,
                  has_key=config.has_api_key())


@app.post("/mini")
def create_mini(title: str = Form(...), goal: str = Form(""), tone: str = Form("")):
    project = _current_project()
    mid = db.create_mini_project(project["id"], title.strip(), goal.strip(), tone.strip())
    return redirect(f"/mini/{mid}")


@app.get("/mini/{mid}", response_class=HTMLResponse)
def mini_detail(request: Request, mid: int):
    mini = db.get_mini_project(mid)
    if not mini:
        return redirect("/")
    takes = db.list_takes(mid)
    return render(request, "mini.html", mini=mini, takes=takes,
                  has_key=config.has_api_key())


@app.post("/mini/{mid}/take")
def create_take(mid: int,
                language: str = Form("english"),
                intended_message: str = Form(""),
                source_text: str = Form(""),
                audio: Optional[UploadFile] = File(None)):
    mini = db.get_mini_project(mid)
    if not mini:
        return redirect("/")

    audio_path = ""
    kind = "text"
    if audio is not None and audio.filename:
        kind = "audio"
        suffix = Path(audio.filename).suffix or ".m4a"
        dest = config.AUDIO_DIR / f"take_{int(time.time()*1000)}{suffix}"
        with open(dest, "wb") as f:
            f.write(audio.file.read())
        audio_path = str(dest)

    take_id = db.create_take(
        mid, kind, language.strip(), intended_message.strip(),
        source_text=source_text.strip(), audio_path=audio_path,
    )
    worker.enqueue(take_id)
    return redirect(f"/take/{take_id}")


@app.get("/take/{take_id}", response_class=HTMLResponse)
def take_detail(request: Request, take_id: int):
    take = db.get_take(take_id)
    if not take:
        return redirect("/")
    mini = db.get_mini_project(take["mini_project_id"])
    transcript = db.get_transcript(take_id)
    report = db.get_report(take_id)
    return render(request, "take.html", take=take, mini=mini,
                  transcript=transcript, report=report)


@app.get("/take/{take_id}/status")
def take_status(take_id: int):
    take = db.get_take(take_id)
    if not take:
        return {"status": "missing"}
    return {"status": take["status"], "error": take["error"]}


@app.get("/health")
def health():
    return {"ok": True, "has_api_key": config.has_api_key()}
