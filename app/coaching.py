"""The coaching brain.

Given a take's transcript (plus the goal/tone of its project and mini-project,
and what the user *intended* to say), ask the model to:

  1. Act as the LISTENER and state back, in one sentence, what it understood the
     point to be — BEFORE being told the intended message. This "heard_message"
     vs the user's "intended_message" is the meant-vs-heard gap that this whole
     app exists to shrink.
  2. Score the delivery on a structure/clarity rubric (not interview performance).
  3. Give concrete what-worked / patterns-to-fix / next-rep guidance.

Only transcript text + metrics go to the model. Audio never leaves the machine.
"""
from __future__ import annotations

from typing import Any, Dict, Optional

import anthropic

from . import config

REPORT_TOOL = {
    "name": "write_coaching_report",
    "description": "Record a structured articulation-coaching report for one take.",
    "input_schema": {
        "type": "object",
        "properties": {
            "heard_message": {
                "type": "string",
                "description": "In ONE sentence, the single main point you (as a "
                               "first-time listener) actually took away. Decide this "
                               "from the transcript alone.",
            },
            "gap_note": {
                "type": "string",
                "description": "How your heard_message differs from what the speaker "
                               "INTENDED to land (provided separately). If they match "
                               "well, say so. If the intended point never came across, "
                               "say that plainly — this is the most important field.",
            },
            "overall_summary": {
                "type": "string",
                "description": "2-4 sentences on how clearly the point was delivered.",
            },
            "clarity_scores": {
                "type": "object",
                "description": "Score each dimension 1 (poor) to 5 (excellent) with a "
                               "one-line note grounded in the transcript.",
                "properties": {
                    "lead":        {"type": "object", "properties": {"score": {"type": "integer"}, "note": {"type": "string"}}, "required": ["score", "note"]},
                    "through_line":{"type": "object", "properties": {"score": {"type": "integer"}, "note": {"type": "string"}}, "required": ["score", "note"]},
                    "order":       {"type": "object", "properties": {"score": {"type": "integer"}, "note": {"type": "string"}}, "required": ["score", "note"]},
                    "signposting": {"type": "object", "properties": {"score": {"type": "integer"}, "note": {"type": "string"}}, "required": ["score", "note"]},
                    "landing":     {"type": "object", "properties": {"score": {"type": "integer"}, "note": {"type": "string"}}, "required": ["score", "note"]},
                },
                "required": ["lead", "through_line", "order", "signposting", "landing"],
            },
            "what_worked": {
                "type": "array",
                "description": "Specific things done well, quoting the transcript.",
                "items": {
                    "type": "object",
                    "properties": {
                        "quote": {"type": "string"},
                        "why": {"type": "string"},
                    },
                    "required": ["quote", "why"],
                },
            },
            "top_patterns": {
                "type": "array",
                "description": "The biggest recurring clarity problems, most important first.",
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
                     "clarity_scores", "what_worked", "top_patterns", "next_rep"],
    },
}


def _build_prompt(transcript: str, metrics: Dict[str, Any], *,
                  project_goal: str, project_tone: str,
                  mini_goal: str, mini_tone: str,
                  intended_message: str, language: str) -> str:
    metric_lines = ", ".join(
        f"{k}={v}" for k, v in metrics.items() if v is not None
    )
    return f"""You are an articulation coach. The speaker is practicing delivering ONE idea clearly. Their overarching goal is to close the gap between what they mean and what listeners actually understand.

CONTEXT
- Project goal: {project_goal}
- Project tone: {project_tone}
- This topic's goal: {mini_goal or '(none given)'}
- This topic's tone: {mini_tone or '(inherits project tone)'}
- Language of this take: {language}
- Mechanical metrics: {metric_lines or '(none)'}

CRITICAL — do this in order:
1. FIRST, read ONLY the transcript below and decide, as a fresh listener, the single main point you took away. That is `heard_message`. Do not peek at the intended message for this step.
2. THEN compare it to what the speaker INTENDED to land:
   INTENDED: {intended_message or '(speaker did not state an intended message)'}
   Put the comparison in `gap_note`. If the intended point did not come across, say so directly — that gap is the whole point of this exercise.
3. Score the rubric and give grounded, quotable feedback. Judge STRUCTURE and CLARITY (did they lead with the point? one through-line? logical order? signposting? clean landing?), not charisma or correctness of content.

Be specific and quote the transcript. Be honest, not flattering.

TRANSCRIPT
\"\"\"
{transcript}
\"\"\"

Call the write_coaching_report tool with your analysis."""


def synthesize(transcript: str, metrics: Dict[str, Any], *,
               project_goal: str = "", project_tone: str = "",
               mini_goal: str = "", mini_tone: str = "",
               intended_message: str = "", language: str = "english"
               ) -> Dict[str, Any]:
    """Generate a coaching report. Raises if no API key or the call fails."""
    if not config.has_api_key():
        raise RuntimeError(
            "ANTHROPIC_API_KEY is not set. Add it to your .env file."
        )

    client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)
    prompt = _build_prompt(
        transcript, metrics,
        project_goal=project_goal, project_tone=project_tone,
        mini_goal=mini_goal, mini_tone=mini_tone,
        intended_message=intended_message, language=language,
    )

    resp = client.messages.create(
        model=config.COACH_MODEL,
        max_tokens=2000,
        tools=[REPORT_TOOL],
        tool_choice={"type": "tool", "name": "write_coaching_report"},
        messages=[{"role": "user", "content": prompt}],
    )

    for block in resp.content:
        if block.type == "tool_use" and block.name == "write_coaching_report":
            return block.input  # type: ignore[return-value]
    raise RuntimeError("Model did not return a coaching report.")
