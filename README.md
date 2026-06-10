# Learning Coach

A personal, AI-assisted learning companion. You pick something you want to learn,
work it down to a clear point, then **practice articulating it** — and the app tells
you *what a listener actually heard* versus what you meant. The goal: close the gap
between what you know and what comes across, and practice sounding like the person
you want to become.

The loop: **learn → research → analyze → summarize → record & articulate → practice → repeat.**
This first version implements the **articulate → coach → practice** spine; the
research/summarize tutor stages come next.

## How it works

- **Projects** carry a global goal + tone. Under them, **topics** (mini-projects) each
  have their own goal/tone.
- A **take** is one attempt at articulating an idea — pasted text now, or audio
  (transcribed locally) soon.
- Each take gets a **coaching report**: the *heard-vs-meant* gap, a structure/clarity
  rubric (lead, through-line, order, signposting, landing), what worked, patterns to
  fix, and a next-rep suggestion.

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

Binds to `0.0.0.0:8000` so it's reachable over **Tailscale** — open
`http://<your-mac-mini-tailscale-ip>:8000` from your phone.

## Stack

Python · FastAPI · SQLite · Jinja2 · Anthropic (Sonnet) for coaching ·
local `mlx-whisper` for audio transcription (Apple Silicon).
