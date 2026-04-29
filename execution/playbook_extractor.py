"""
Given an agent playbook (markdown), suggest an AI Roleplay Config JSON
matching the runtime contract used by conversation_manager.py.

The output is a SUGGESTION — the manager always reviews/edits before publishing.
Conservative by design: only extracts what's clearly stated; leaves arrays short
when uncertain rather than fabricating objections.
"""
import os
import json
import logging

from anthropic import Anthropic
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

EXTRACTION_MODEL = "claude-sonnet-4-5"

SCHEMA_EXAMPLE = {
    "persona": {
        "type": "sponsored_lead",
        "sponsors": [{"name": "Sample", "relationship": "friend"}],
        "moods": ["curious", "skeptical", "busy"],
        "pain_points": ["time", "cost", "trust"],
        "remembers_sponsorship_probability": 0.5,
    },
    "objections": {
        "beginner": [
            {"type": "confusion", "statement": "What is this again?", "weight": 9},
        ],
        "intermediate": [
            {"type": "not_interested", "statement": "I'm not interested.", "weight": 10},
        ],
        "advanced": [
            {"type": "spouse_decision", "statement": "I'd have to talk to my spouse.", "weight": 10},
        ],
    },
}

SYSTEM_PROMPT = """You convert a sales agent's call script into a JSON config that drives a roleplay AI customer for training purposes.

Rules:
- Output ONLY valid JSON. No prose, no markdown fences.
- Be conservative. Only include objections explicitly mentioned or strongly implied in the script.
- NEVER invent specific sponsor names. Use the placeholder {"name": "Sample", "relationship": "friend"} unless the script clearly defines a referral relationship.
- Spread objections across difficulty levels: beginner (3 simple), intermediate (3 standard), advanced (2-3 complex). If the script doesn't have enough material, leave a level empty rather than padding.
- Each objection needs: type (snake_case), statement (verbatim or near-verbatim customer line), weight (1-10).
- Pick moods (3-5) and pain_points (3-5) that match the customer profile in the script.
- remembers_sponsorship_probability: 0.6 if there's a clear sponsor/referral concept, 0.1 for cold calls, 0.5 otherwise.
"""


def _build_prompt(playbook_markdown):
    return f"""Here is the agent's call script (the playbook the human trainee recites):

<playbook>
{playbook_markdown.strip()}
</playbook>

Match this exact JSON shape (this is the runtime contract):

<schema_example>
{json.dumps(SCHEMA_EXAMPLE, indent=2)}
</schema_example>

Return ONLY the filled-in JSON for the persona + objections blocks (no other keys). No markdown, no commentary."""


def _validate(suggestion):
    """Loose validation. Returns (ok, reason)."""
    if not isinstance(suggestion, dict):
        return False, "not a dict"
    persona = suggestion.get("persona") or {}
    if not isinstance(persona.get("sponsors"), list) or not persona["sponsors"]:
        return False, "persona.sponsors empty"
    objections = suggestion.get("objections") or {}
    if not isinstance(objections, dict):
        return False, "objections not a dict"
    total = sum(
        len(objections.get(d, []) or []) for d in ("beginner", "intermediate", "advanced")
    )
    if total == 0:
        return False, "no objections at any difficulty"
    return True, "ok"


def stub_suggestion():
    """Fallback when extraction fails — gives the manager a starting form to edit."""
    return {
        "persona": {
            "type": "lead",
            "sponsors": [{"name": "Sample", "relationship": "friend"}],
            "moods": ["curious", "skeptical", "busy"],
            "pain_points": ["time", "cost", "trust"],
            "remembers_sponsorship_probability": 0.5,
        },
        "objections": {
            "beginner": [],
            "intermediate": [],
            "advanced": [],
        },
    }


def suggest_roleplay_from_playbook(playbook_markdown):
    """Run the extraction. Returns (suggestion_dict, note_str)."""
    if not playbook_markdown or len(playbook_markdown.strip()) < 50:
        return stub_suggestion(), "Playbook too short to auto-extract — please fill in manually."

    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        return stub_suggestion(), "ANTHROPIC_API_KEY missing — please fill in manually."

    client = Anthropic(api_key=api_key, max_retries=2, timeout=60.0)
    try:
        resp = client.messages.create(
            model=EXTRACTION_MODEL,
            max_tokens=2000,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": _build_prompt(playbook_markdown)}],
        )
        text = "".join(block.text for block in resp.content if hasattr(block, "text"))
        text = text.strip()
        # Strip code fences if present
        if text.startswith("```"):
            text = text.split("```", 2)[1]
            if text.startswith("json"):
                text = text[4:]
            text = text.strip().rstrip("`").strip()
        suggestion = json.loads(text)
    except json.JSONDecodeError as e:
        logger.warning(f"Extraction returned non-JSON: {e}")
        return stub_suggestion(), "Claude returned an unparseable response — please fill in manually."
    except Exception as e:
        logger.exception(f"Extraction error: {e}")
        return stub_suggestion(), f"Extraction failed ({type(e).__name__}) — please fill in manually."

    ok, reason = _validate(suggestion)
    if not ok:
        logger.warning(f"Extraction validation failed: {reason}")
        return stub_suggestion(), f"Extraction was incomplete ({reason}) — please review manually."

    return suggestion, "Auto-extracted from your playbook. Review and edit as needed before publishing."
