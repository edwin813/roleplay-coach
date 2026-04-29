"""
Response Scoring - Evaluates agent responses against objection library and scoring rubric.
"""
import os
import json
import logging
import hashlib
from typing import Dict, Any, List
from dotenv import load_dotenv
from api_retry import with_retry, classify_api_error

try:
    from anthropic import Anthropic
except ImportError:
    Anthropic = None

load_dotenv()

logger = logging.getLogger(__name__)

class ResponseScorer:
    """Scores agent responses using AI-powered evaluation."""

    def __init__(self):
        if not Anthropic:
            raise ImportError("Anthropic SDK not installed")

        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY not found in .env")

        self.client = Anthropic(
            api_key=api_key,
            max_retries=3,  # Built-in Anthropic SDK retry
            timeout=60.0    # 60 second timeout
        )

        # Response cache for reducing redundant API calls
        self._score_cache = {}

    def _cache_key(self, text: str) -> str:
        """Generate cache key from text."""
        return hashlib.md5(text.encode()).hexdigest()

    def score_objection_response(self, objection_type: str, customer_statement: str,
                                  agent_response: str) -> Dict[str, Any]:
        """
        Score how well the agent handled an objection.

        Args:
            objection_type: Type of objection (price, timing, coverage, etc.)
            customer_statement: What the customer said
            agent_response: How the agent responded

        Returns:
            Dictionary with score and feedback
        """
        # Define scoring criteria based on objection type
        criteria = self._get_objection_criteria(objection_type)

        prompt = f"""You are evaluating a benefits enrollment agent using the Plus Lead phone script. The agent calls leads who were referred by a sponsor (union member, veteran, police officer, or teacher) to activate a private benefits package (life insurance).

OBJECTION TYPE: {objection_type}
CUSTOMER SAID: "{customer_statement}"
AGENT RESPONDED: "{agent_response}"

SCORING CRITERIA (from the company's approved objection library):
{criteria}

Evaluate the agent's response on a scale of 0-10:

SCORE the response based on:
1. Did they hit the required response elements listed above?
2. Did they reference the sponsor appropriately?
3. Did they reframe the conversation back to activating benefits?
4. Was the tone confident but not pushy?
5. Did they avoid common mistakes (accepting "not interested", skipping sponsor name, etc.)?

PROVIDE:
1. Score (0-10)
2. What they did well (specific examples from the script)
3. What they could improve (specific suggestions referencing the required elements)
4. How many key points from the criteria they hit

Format your response as JSON:
{{
  "score": <number 0-10>,
  "strengths": ["<specific strength 1>", "<specific strength 2>"],
  "improvements": ["<specific improvement 1>", "<specific improvement 2>"],
  "key_points_hit": <number of key points successfully addressed>,
  "feedback_summary": "<brief overall assessment>"
}}"""

        # Check cache first
        cache_key = self._cache_key(f"{objection_type}:{agent_response}")
        if cache_key in self._score_cache:
            logger.info(f"📦 Using cached score for objection response")
            return self._score_cache[cache_key]

        # Make API call with retry logic
        try:
            def make_api_call():
                return self.client.messages.create(
                    model="claude-haiku-4-5-20251001",
                    max_tokens=300,
                    messages=[{"role": "user", "content": prompt}]
                )

            response = with_retry(make_api_call, max_retries=5)

            # Parse JSON response
            result = json.loads(response.content[0].text)
            result["success"] = True
            result["objection_type"] = objection_type

            # Cache the result
            self._score_cache[cache_key] = result
            return result

        except json.JSONDecodeError:
            # Fallback if not valid JSON
            result = {
                "success": False,
                "error": "Could not parse AI response",
                "raw_response": response.content[0].text
            }
        except Exception as e:
            # Handle API errors gracefully
            error_info = classify_api_error(e)
            logger.error(f"❌ Scoring error: {error_info['technical_message']}")

            result = {
                "success": False,
                "score": 5,  # Neutral score
                "feedback": f"Unable to score response: {error_info['user_message']}",
                "error_type": error_info['type'],
                "retryable": error_info['retryable']
            }

    def score_tone_confidence(self, transcript: str, audio_metadata: Dict = None) -> Dict[str, Any]:
        """
        Score agent's tone and confidence based on transcript.

        Args:
            transcript: What the agent said
            audio_metadata: Optional audio analysis data (pace, volume, etc.)

        Returns:
            Dictionary with tone/confidence score
        """
        prompt = f"""Analyze this benefits enrollment agent's speech for tone and confidence. They are using the Plus Lead phone script to activate a sponsor-referred benefits package.

AGENT SAID: "{transcript}"

Evaluate on a scale of 0-10:
- Voice Clarity: Is it easy to understand, professional language?
- Confidence Level: Do they sound assured and knowledgeable about the benefits?
- Energy: Are they engaged and enthusiastic without being pushy?
- Professionalism: Appropriate tone — friendly, confident, like they're doing the lead a favor?

Look for:
- Filler words (um, uh, like) — some is natural, excessive is a problem
- Hesitation or uncertainty about the benefits/process
- Overly aggressive or pushy language (should sound helpful, not salesy)
- Natural conversational tone (not robotic script reading)

Respond in JSON:
{{
  "score": <0-10>,
  "clarity": <0-10>,
  "confidence": <0-10>,
  "energy": <0-10>,
  "issues": ["<issue 1>", "<issue 2>"],
  "feedback": "<brief assessment>"
}}"""

        # Check cache first
        cache_key = self._cache_key(f"tone:{transcript}")
        if cache_key in self._score_cache:
            logger.info(f"📦 Using cached tone/confidence score")
            return self._score_cache[cache_key]

        # Make API call with retry logic
        try:
            def make_api_call():
                return self.client.messages.create(
                    model="claude-haiku-4-5-20251001",
                    max_tokens=300,
                    messages=[{"role": "user", "content": prompt}]
                )

            response = with_retry(make_api_call, max_retries=5)

            result = json.loads(response.content[0].text)
            result["success"] = True

            # Cache the result
            self._score_cache[cache_key] = result
            return result

        except json.JSONDecodeError:
            result = {
                "success": False,
                "error": "Could not parse response",
                "raw": response.content[0].text
            }
        except Exception as e:
            # Handle API errors gracefully
            error_info = classify_api_error(e)
            logger.error(f"❌ Tone scoring error: {error_info['technical_message']}")

            result = {
                "success": False,
                "score": 7,  # Neutral score
                "feedback": f"Unable to score tone: {error_info['user_message']}",
                "error_type": error_info['type'],
                "retryable": error_info['retryable']
            }

        return result

    def score_full_session(self, conversation_history: List[Dict],
                          objections_presented: List[Dict]) -> Dict[str, Any]:
        """
        Score entire training session across all categories.

        Args:
            conversation_history: Full conversation transcript
            objections_presented: List of objections and responses

        Returns:
            Complete scoring breakdown
        """
        # Category scores
        objection_scores = []
        tone_scores = []

        # Score each objection
        for msg in conversation_history:
            if msg["role"] == "agent" and msg.get("objection_evaluated"):
                objection_scores.append(msg["score"])

        # Score tone from agent messages
        agent_messages = [msg["content"] for msg in conversation_history if msg["role"] == "agent"]
        if agent_messages:
            # Score overall tone
            combined_text = " ".join(agent_messages[:3])  # First 3 responses
            tone_result = self.score_tone_confidence(combined_text)
            tone_score = tone_result.get("score", 7)
        else:
            tone_score = 0

        # Calculate category scores (simplified)
        objection_handling = sum(objection_scores) / len(objection_scores) if objection_scores else 0
        tone_confidence = tone_score
        script_adherence = 8  # Would evaluate against actual script
        active_listening = 8  # Would evaluate based on response relevance
        professionalism = 9  # Would check for issues

        # Weighted final score (from score_performance.md)
        final_score = (
            objection_handling * 0.40 +
            tone_confidence * 0.20 +
            script_adherence * 0.15 +
            active_listening * 0.15 +
            professionalism * 0.10
        )

        return {
            "success": True,
            "final_score": round(final_score, 1),
            "category_scores": {
                "objection_handling": round(objection_handling, 1),
                "tone_confidence": round(tone_confidence, 1),
                "script_adherence": round(script_adherence, 1),
                "active_listening": round(active_listening, 1),
                "professionalism": round(professionalism, 1)
            },
            "grade": self._get_grade(final_score),
            "objections_handled": len(objection_scores),
            "needs_trainer_followup": final_score < 7.0
        }

    def _get_objection_criteria(self, objection_type: str) -> str:
        """Get scoring criteria for specific objection type."""
        criteria_map = {
            "confusion": """
Key elements agent should include:
1. Identify the specific benefits: "These are the benefits that [sponsor] set up for you"
2. Mention privacy: benefits are private and reviewed in secure portal
3. Explain sponsor relationship: [sponsor] is a veteran/union member/police officer/teacher
4. Clarify extension: "[sponsor] was able to extend that access to you"
            """,
            "not_interested": """
Key elements (agent must hit ALL 4):
1. Address confusion: "Oh there might be some confusion"
2. Remind about sponsor: "[sponsor] included you in their family benefits"
3. Reframe: "There isn't anything to be interested in, [sponsor] already set it up for you"
4. State obligation: "I just promised [sponsor] I would go over it with you"
            """,
            "cost": """
Key elements (agent must hit at least 5 of 7):
1. Reference text: "You must have not read the text that [sponsor] sent"
2. Free policy: "I'm going to issue you a $2,000 policy for free"
3. Needs analysis: "We will complete a no-cost needs analysis for your family"
4. Conditional options: "IF there is a need and IF you qualify, I can show options"
5. No promises: "I don't even know if you'll qualify so I can't make promises"
6. Confirm free policy: "I can promise we'll issue the free $2,000 policy"
7. Portal requirement: "We can only do that in the secure benefits portal"
            """,
            "busy": """
Key elements (agent must hit at least 5 of 7):
1. Acknowledge: "I totally understand, I'm too busy to go over all of this right now"
2. Pivot to scheduling: "I'm just calling to schedule a time"
3. Reframe purpose: "We are going to activate ALL of the benefits [sponsor] set up"
4. Offer time options: "When are you most available? Mornings, afternoons, or evenings?"
5. Give two specific slots on the same day
6. Text confirmation: Ask them to text back "CONFIRM"
7. Commitment close: "We do ask that if you book the appointment, to commit to it"
            """,
            "need_permission": """
Key elements (agent must hit ALL 4):
1. Acknowledge: "[sponsor] asked me to explain this since it's important for your family"
2. Reassurance: "They mentioned you might want a little bit of reassurance"
3. Reference text: "That's why we sent you that text ahead of time"
4. Emphasize effort: "[sponsor] went out of their way to make sure you were prepared"
            """,
            "coverage": """
Key elements agent should include:
1. Acknowledge: "That's exactly why I'm calling"
2. Reference sponsor: "[sponsor] mentioned you might already have something in place"
3. Position as complementary: "These benefits complement the insurance you already have"
4. Logic statement: "This wouldn't make sense for you if you didn't already have something"
            """,
            "no_text": """
Key elements:
1. Offer to resend: "Let me resend it from the group text with [sponsor]"
2. Confirm number: "Do you receive texts to this number?"
3. Action statement: "I just resent it"
4. Get confirmation: "Let me know when you receive it"
            """,
            "timing": """
Key elements:
1. Acknowledge: "Great question"
2. Set expectation: "I told [sponsor] I would set aside 30-45 minutes for you"
3. Explain purpose: "We'll be going over all the private benefits [sponsor] set up"
            """
        }
        return criteria_map.get(objection_type, "General Plus Lead objection handling: agent should reference the sponsor, reframe as activating existing benefits, and maintain confident but friendly tone.")

    def _get_grade(self, score: float) -> str:
        """Convert score to grade."""
        if score >= 9.0:
            return "Excellent"
        elif score >= 7.0:
            return "Good"
        elif score >= 5.0:
            return "Needs Improvement"
        else:
            return "Not Ready"

if __name__ == "__main__":
    scorer = ResponseScorer()

    # Test objection scoring
    result = scorer.score_objection_response(
        objection_type="price",
        customer_statement="This seems really expensive. I'm not sure I can afford $150 per month.",
        agent_response="I understand that budget is important. Let me break this down - $150 per month is only $5 per day, about the cost of a coffee. And this protects your entire family's future. What's your main concern - is it the monthly amount or understanding the value?"
    )

    print("Objection Handling Score:")
    print(f"  Score: {result['score']}/10")
    print(f"  Strengths: {', '.join(result['strengths'])}")
    print(f"  Summary: {result['feedback_summary']}")
