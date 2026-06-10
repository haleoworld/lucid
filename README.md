# Lucid

A personal, AI-assisted learning companion. You pick something you want to learn,
work it down to a clear point, then **practice articulating it** — and the app tells
you *what a listener actually heard* versus what you meant. The goal: close the gap
between what you know and what comes across, and practice sounding like the person
you envision becoming.

The loop: **learn → research → analyze → summarize → record & articulate → practice → repeat.**
This first version implements the **articulate → coach → practice** spine; the
research/summarize tutor stages come next.

## How it works

- **Projects** carry a global goal + tone. Under them, **topics** (mini-projects) are
  the things you practice — each with a domain (work / relationship / social / sales /
  learning), a situation, a goal, and a **target tone** (your envisioned self).
- **Prep** (tutor stage): generate a study brief for a topic — how to improve, **cited
  sources from a live web search** (YouTube videos, articles), key points, a suggested
  through-line, an outline, example phrasings in your target tone, and pitfalls.
- A **take** is one attempt — pasted text or **audio (transcribed locally via
  mlx-whisper)**.
- Each take gets a **coaching report**: the *heard-vs-meant* gap, plus a **dynamic
  rubric** whose dimensions are chosen to fit the scenario (a demo is scored on
  structure; "calm my kid without lecturing" on tone-match, warmth, and landing without
  resistance), what worked, patterns to fix, and a next rep. Telegram pings on done/fail.

## Privacy

- Audio and transcripts stay on this machine (`data/`, gitignored). Only transcript
  **text** is sent to the model for coaching.
- Secrets live in `.env` (gitignored). **Nothing private is committed** — this repo is
  code only.

## Run it

```bash
cp .env.example .env        # then put your ANTHROPIC_API_KEY in .env
./run.sh
```

Binds to `0.0.0.0:8042` so it's reachable over **Tailscale**. For a tidy HTTPS path:
`tailscale serve --bg --set-path /lucid http://127.0.0.1:8042` (set `URL_PREFIX=/lucid`).
For always-on across reboots, see `deploy/com.lucid.app.plist.example`.
Audio transcription is optional (Apple Silicon): `pip install -r requirements-audio.txt`
plus `brew install ffmpeg`.

## Stack

Python · FastAPI · SQLite · Jinja2 · Anthropic (Sonnet) for coaching ·
local `mlx-whisper` for audio transcription (Apple Silicon).
