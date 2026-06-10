"""The coaching brain.

Two jobs:

1. synthesize() — given a take's transcript (+ the scenario, goal, target tone,
   and what the user *intended*), produce a coaching report. It:
     a. acts as the listener / the other person and states back how the message
        would actually land — the meant-vs-heard gap this app exists to shrink;
     b. scores DYNAMIC, scenario-appropriate dimensions (a work demo is judged on
        structure/clarity; "defuse my wife wittily" is judged on tone-match,
        warmth, and whether it lands without resistance — NOT on "signposting");
     c. gives grounded what-worked / patterns / next-rep guidance.

2. prep() — the tutor stage. Uses web search to find reliable, cited sources
   (YouTube videos, articles) on improving at this specific scenario, then
   produces a prep brief: how to improve, key points, a suggested through-line,
   an outline, example phrasings (for scenarios), and pitfalls.

Only transcript text + scenario metadata go to the model. Audio stays local.
"""
from __future__ import annotations

from typing import Any, Dict, List

import anthropic

from . import config

WEB_SEARCH_TOOL = {"type": "web_search_20250305", "name": "web_search", "max_uses": 5}

REPORT_TOOL = {
    "name": "write_coaching_report",
    "description": "Record a structured articulation-coaching report for one take.",
    "input_schema": {
        "type": "object",
        "properties": {
            "heard_message": {
                "type": "string",
                "description": "In ONE sentence, how a fresh listener — or the other "
                               "person in this scenario — would most likely receive your "
                               "main message AND react to your tone. Decide from the "
                               "transcript alone, before reading the intended message.",
            },
            "gap_note": {
                "type": "string",
                "description": "How heard_message differs from what the speaker INTENDED "
                               "(provided separately). If the intent didn't land, or the "
                               "tone would provoke resistance, say so plainly — this is "
                               "the most important field.",
            },
            "overall_summary": {
                "type": "string",
                "description": "2-4 sentences on how well this take served its goal and tone.",
            },
            "dimensions": {
                "type": "array",
                "description": "4-6 rubric dimensions CHOSEN to fit THIS scenario and its "
                               "target tone. For an explain/teach scenario use clarity "
                               "dimensions (lead, through-line, order, signposting, "
                               "landing). For an interpersonal/sales scenario use ones "
                               "like tone-match, warmth, lands-without-resistance, "
                               "brevity (not lecturing), reading-the-room, authority. "
                               "Score each 1 (poor) to 5 (excellent).",
                "items": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"},
                        "score": {"type": "integer"},
                        "note": {"type": "string", "description": "One line, grounded in the transcript."},
                    },
                    "required": ["name", "score", "note"],
                },
            },
            "what_worked": {
                "type": "array",
                "description": "Specific things done well, quoting the transcript.",
                "items": {
                    "type": "object",
                    "properties": {"quote": {"type": "string"}, "why": {"type": "string"}},
                    "required": ["quote", "why"],
                },
            },
            "top_patterns": {
                "type": "array",
                "description": "The biggest recurring problems, most important first.",
                "items": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"},
                        "examples": {"type": "array", "items": {"type": "string"}},
                        "fix": {"type": "string"},
                    },
                    "required": ["name", "examples", "fix"],
                },
            },
            "next_rep": {
                "type": "string",
                "description": "One concrete thing to practice on the next take.",
            },
        },
        "required": ["heard_message", "gap_note", "overall_summary",
                     "dimensions", "what_worked", "top_patterns", "next_rep"],
    },
}

PREP_TOOL = {
    "name": "write_prep_brief",
    "description": "Record a study/prep brief for practicing a scenario or topic.",
    "input_schema": {
        "type": "object",
        "properties": {
            "summary": {"type": "string", "description": "Short orientation to this scenario/topic."},
            "how_to_improve": {
                "type": "array", "items": {"type": "string"},
                "description": "Concrete, specific techniques to get better at THIS scenario.",
            },
            "sources": {
                "type": "array",
                "description": "Reliable cited sources found via web search — prefer "
                               "reputable YouTube videos and articles. Use REAL urls.",
                "items": {
                    "type": "object",
                    "properties": {
                        "title": {"type": "string"},
                        "url": {"type": "string"},
                        "kind": {"type": "string", "description": "video | article | other"},
                        "why": {"type": "string", "description": "Why it's worth your time."},
                    },
                    "required": ["title", "url", "why"],
                },
            },
            "key_points": {
                "type": "array", "items": {"type": "string"},
                "description": "The substance to internalize before recording.",
            },
            "suggested_throughline": {
                "type": "string",
                "description": "The single spine to build your take around.",
            },
            "outline": {
                "type": "array", "items": {"type": "string"},
                "description": "Ordered beats for the take.",
            },
            "example_phrasings": {
                "type": "array", "items": {"type": "string"},
                "description": "Sample lines in the TARGET TONE (especially for "
                               "interpersonal/sales scenarios).",
            },
            "pitfalls": {
                "type": "array", "items": {"type": "string"},
                "description": "What to avoid (e.g. lecturing, rambling, sounding defensive).",
            },
        },
        "required": ["summary", "how_to_improve", "sources", "key_points",
                     "suggested_throughline", "outline", "pitfalls"],
    },
}


def _client() -> anthropic.Anthropic:
    if not config.has_api_key():
        raise RuntimeError("ANTHROPIC_API_KEY is not set. Add it to your .env file.")
    return anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)


def _tool_input(resp, tool_name: str):
    for block in resp.content:
        if getattr(block, "type", None) == "tool_use" and block.name == tool_name:
            return block.input
    return None


# --- coaching report --------------------------------------------------------

def _coach_prompt(transcript, metrics, *, project_goal, project_tone, title,
                  domain, situation, mini_goal, mini_tone, intended_message, language):
    metric_lines = ", ".join(f"{k}={v}" for k, v in metrics.items() if v is not None)
    return f"""You are an articulation & interpersonal-communication coach. The speaker is practicing toward the person they envision becoming. Their overarching goal: close the gap between what they mean and how it actually lands on others.

SCENARIO
- Topic: {title}
- Domain: {domain}
- Situation being practiced: {situation or '(general articulation practice)'}
- What success looks like (goal): {mini_goal or project_goal}
- Target tone (their envisioned self): {mini_tone or project_tone or '(clear and natural)'}
- Language: {language}
- Mechanical metrics: {metric_lines or '(none)'}

DO THIS IN ORDER:
1. Read ONLY the transcript and decide how a fresh listener — or the other person in this situation — would actually receive the message and react to the tone. That is `heard_message`. Don't peek at the intended message yet.
2. Compare to what they INTENDED: {intended_message or '(not stated)'} → put it in `gap_note`. If the intent didn't land, or the tone would create resistance/defensiveness, say so directly.
3. CHOOSE 4-6 rubric `dimensions` that actually fit THIS scenario and target tone. Do NOT force clarity dimensions onto an interpersonal scenario. Examples:
   - explain/demo/report → lead, through-line, order, signposting, landing
   - calm a partner / redirect a child / chat with a friend → tone-match, warmth, lands-without-resistance, brevity (not lecturing), reading-the-room, lightness/humour
   - sales / influence up → authority, clarity, asks-good-questions, builds-trust, handles-pushback
4. Give grounded, quotable what-worked, top patterns, and one next rep.

Judge whether it serves the goal and TONE — not charisma or factual correctness. Be specific, quote the transcript, be honest not flattering.

TRANSCRIPT
\"\"\"
{transcript}
\"\"\"

Call write_coaching_report with your analysis."""


def synthesize(transcript: str, metrics: Dict[str, Any], *,
               title: str = "", domain: str = "learning", situation: str = "",
               project_goal: str = "", project_tone: str = "",
               mini_goal: str = "", mini_tone: str = "",
               intended_message: str = "", language: str = "english") -> Dict[str, Any]:
    client = _client()
    prompt = _coach_prompt(
        transcript, metrics, project_goal=project_goal, project_tone=project_tone,
        title=title, domain=domain, situation=situation, mini_goal=mini_goal,
        mini_tone=mini_tone, intended_message=intended_message, language=language)
    resp = client.messages.create(
        model=config.COACH_MODEL, max_tokens=2500,
        tools=[REPORT_TOOL],
        tool_choice={"type": "tool", "name": "write_coaching_report"},
        messages=[{"role": "user", "content": prompt}],
    )
    out = _tool_input(resp, "write_coaching_report")
    if out is None:
        raise RuntimeError("Model did not return a coaching report.")
    return out


# --- prep / tutor stage -----------------------------------------------------

def _prep_prompt(*, title, domain, situation, goal, tone, language):
    return f"""You are a learning coach preparing someone to practice articulating the scenario below, in the voice of the person they want to become.

SCENARIO
- Topic: {title}
- Domain: {domain}
- Situation: {situation or '(general practice)'}
- Goal (what should land): {goal or '(communicate it clearly and well)'}
- Target tone: {tone or '(clear, natural)'}
- Practice language: {language}

STEPS:
1. Use web_search to find a few RELIABLE, high-quality sources on how to get better at this specific kind of communication — prefer reputable YouTube videos and articles. Capture their real titles and URLs.
2. Then call write_prep_brief with: a short summary, concrete how-to-improve techniques, the cited sources, the key points to internalize, a single suggested through-line, an ordered outline for the take, example phrasings in the TARGET TONE (especially important for interpersonal/sales scenarios), and pitfalls to avoid.

Make it practical and specific to THIS scenario — not generic advice. Finish by calling write_prep_brief."""


def prep(*, title: str, domain: str = "learning", situation: str = "",
         goal: str = "", tone: str = "", language: str = "english") -> Dict[str, Any]:
    """Generate a prep brief with cited sources. Falls back to no-web-search."""
    client = _client()
    prompt = _prep_prompt(title=title, domain=domain, situation=situation,
                          goal=goal, tone=tone, language=language)
    messages = [{"role": "user", "content": prompt}]

    # Try with web search; if the API can't use it, retry without (model knowledge).
    for tools in ([WEB_SEARCH_TOOL, PREP_TOOL], [PREP_TOOL]):
        try:
            resp = client.messages.create(
                model=config.COACH_MODEL, max_tokens=3500,
                tools=tools, messages=messages,
            )
        except anthropic.BadRequestError:
            continue
        out = _tool_input(resp, "write_prep_brief")
        if out is not None:
            return out
        # Model answered in text without calling the tool — nudge once.
        messages.append({"role": "assistant", "content": resp.content})
        messages.append({"role": "user", "content": "Now call write_prep_brief with the brief."})
        resp = client.messages.create(
            model=config.COACH_MODEL, max_tokens=3500,
            tools=[PREP_TOOL], tool_choice={"type": "tool", "name": "write_prep_brief"},
            messages=messages,
        )
        out = _tool_input(resp, "write_prep_brief")
        if out is not None:
            return out
    raise RuntimeError("Model did not return a prep brief.")
