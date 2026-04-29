"""
Quality grader — uses Opus to score the customer responses produced by the
config-under-test. Returns a 1-10 score. Never trusts an unparseable reply.
"""
from __future__ import annotations

import json
import re
from typing import Any

GRADER_MODEL = "claude-opus-4-7"

RUBRIC = """You are grading the quality of a roleplay AI's responses. The AI is
playing a potential insurance customer talking to a sales agent. You will see
20 turns: the trainee (sales agent) says something, the AI replies as the customer.

Grade the AI's responses as a SET, on a 1-10 scale, on these criteria combined:

1. **In-character.** The AI sounds like a real person, not a chatbot. No "as an AI",
   no fourth-wall breaks, no narrating emotions in parentheses.
2. **Realistic length.** 1-3 sentences. Not monologues, not one-word.
3. **Conversational variety.** Different phrasings, not robotic templates.
4. **Tone-appropriate.** A skeptical customer sounds skeptical. A busy one sounds busy.
5. **Plausible objections.** When raising objections, they're things real people say.

Score:
- 10 = consistently excellent across all 20
- 8 = mostly good, occasional flat reply
- 6 = passable but noticeable issues
- 4 = frequently off (too long, robotic, or out of character)
- 2 or below = unusable

Reply with ONLY a JSON object: {"score": <float>, "rationale": "<one sentence>"}."""


def grade_responses(client: Any, responses: list[dict[str, str]]) -> float:
    transcript_lines = []
    for i, r in enumerate(responses, 1):
        transcript_lines.append(f"--- turn {i} ({r['id']}) ---")
        transcript_lines.append(f"trainee: {r['trainee']}")
        transcript_lines.append(f"ai customer: {r['ai']}")
    transcript = "\n".join(transcript_lines)

    msg = client.messages.create(
        model=GRADER_MODEL,
        max_tokens=400,
        system=RUBRIC,
        messages=[{"role": "user", "content": transcript}],
    )
    text = ""
    for block in msg.content:
        if hasattr(block, "text"):
            text += block.text

    # Tolerant parse: look for {"score": ...}
    match = re.search(r"\{[^{}]*\"score\"[^{}]*\}", text, re.DOTALL)
    if not match:
        raise ValueError(f"grader returned unparseable response: {text[:200]}")
    parsed = json.loads(match.group(0))
    score = float(parsed["score"])
    if score < 0 or score > 10:
        raise ValueError(f"grader returned out-of-range score: {score}")
    return score
