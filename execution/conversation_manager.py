"""
Conversation Manager - Orchestrates AI-powered training conversations using Claude.
"""
import os
import json
from typing import Dict, Any, List, Optional
from dotenv import load_dotenv

try:
    from anthropic import Anthropic
except ImportError:
    Anthropic = None

from text_filters import clean_text_for_speech

load_dotenv()

class TrainingConversation:
    """Manages a voice training conversation session."""

    def __init__(self, agent_name: str, difficulty_level: str = "intermediate", company_id: str = "ao_globe_life"):
        """
        Initialize a training conversation.

        Args:
            agent_name: Name of agent being trained
            difficulty_level: beginner, intermediate, or advanced
            company_id: Which company script to load from scripts/<id>.json
        """
        self.agent_name = agent_name
        self.difficulty_level = difficulty_level
        self.company_id = company_id
        self.conversation_history = []
        self.objections_presented = []
        self.objections_remaining = []
        self.current_phase = "intro"

        # Session timing for graduated threshold system
        self.session_start_time = None
        self.max_session_duration = 12 * 60  # 12 minutes in seconds

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

        # Load company script
        self.script = self._load_script(company_id)

        # Generate dynamic customer persona
        self.customer_profile = self._generate_customer_profile(difficulty_level)

    def _load_script(self, company_id: str) -> dict:
        """Load a company script from scripts/<company_id>.json."""
        scripts_dir = os.path.join(os.path.dirname(__file__), "..", "scripts")
        script_path = os.path.join(scripts_dir, f"{company_id}.json")
        if not os.path.isfile(script_path):
            # Fall back to AO if requested company missing
            script_path = os.path.join(scripts_dir, "ao_globe_life.json")
        with open(script_path, "r") as f:
            return json.load(f)

    def _generate_customer_profile(self, difficulty: str) -> dict:
        """Generate a realistic customer persona from the loaded company script."""
        import random

        persona = self.script.get("persona", {})
        sponsors = persona.get("sponsors") or [{"name": "Sarah", "relationship": "sister"}]
        moods = persona.get("moods") or ["curious", "skeptical", "busy", "confused"]
        all_pain_points = persona.get("pain_points") or ["time", "cost", "trust", "coverage"]
        remembers_prob = persona.get("remembers_sponsorship_probability", 0.6)

        sponsor = random.choice(sponsors)
        remembers = random.random() < remembers_prob

        num_pain_points = min(2 if difficulty == "beginner" else 3, len(all_pain_points))
        pain_points = random.sample(all_pain_points, k=num_pain_points)

        return {
            'sponsor_name': sponsor['name'],
            'sponsor_relationship': sponsor['relationship'],
            'remembers_sponsorship': remembers,
            'mood': random.choice(moods),
            'pain_points': pain_points,
            'mentioned_topics': [],
            'objections_raised': [],
            'key_facts_learned': {},
            'agent_disclosed': []  # Tracks what agent has revealed (progressive disclosure)
        }

    def _detect_agent_disclosures(self, agent_text: str):
        """Scan agent's message for newly revealed information."""
        text_lower = agent_text.lower()
        profile = self.customer_profile

        # Check if agent mentioned sponsor name
        if profile['sponsor_name'].lower() in text_lower and 'sponsor_name' not in profile['agent_disclosed']:
            profile['agent_disclosed'].append('sponsor_name')

        # Check if agent mentioned relationship
        if profile['sponsor_relationship'].lower() in text_lower and 'sponsor_relationship' not in profile['agent_disclosed']:
            profile['agent_disclosed'].append('sponsor_relationship')

        # Check if agent mentioned benefits/insurance/coverage
        benefit_words = ['benefit', 'insurance', 'coverage', 'plan', 'policy', 'enroll']
        if any(w in text_lower for w in benefit_words) and 'benefits_context' not in profile['agent_disclosed']:
            profile['agent_disclosed'].append('benefits_context')

        # Check if agent mentioned sponsorship
        sponsor_words = ['sponsor', 'signed you up', 'put you down', 'referred', 'set you up']
        if any(w in text_lower for w in sponsor_words) and 'sponsorship' not in profile['agent_disclosed']:
            profile['agent_disclosed'].append('sponsorship')

    def _build_disclosed_profile(self) -> str:
        """Build profile section containing ONLY what the agent has revealed."""
        profile = self.customer_profile
        disclosed = profile['agent_disclosed']
        lines = []

        # Always include internal state (mood, busyness)
        lines.append(f"- Your current mood: {profile['mood']}")
        lines.append(f"- You're at home or at work, mildly busy")

        # Only include sponsor info if agent mentioned it
        if 'sponsor_name' in disclosed:
            lines.append(f"- The caller mentioned someone named {profile['sponsor_name']}")
        if 'sponsor_relationship' in disclosed:
            lines.append(f"- {profile['sponsor_name']} is your {profile['sponsor_relationship']}")
        if 'sponsorship' in disclosed:
            memory = "vaguely remember" if profile['remembers_sponsorship'] else "don't remember"
            lines.append(f"- You {memory} being signed up for anything")
        if 'benefits_context' in disclosed:
            lines.append(f"- The caller is talking about some kind of benefits")
            lines.append(f"- Your concerns about this: {', '.join(profile['pain_points'])}")

        return "\n".join(lines)

    def load_objection_library(self) -> List[Dict]:
        """Load objection library from the loaded company script."""
        objections = self.script.get("objections", {})
        return objections.get(self.difficulty_level) or objections.get("intermediate") or []

    def start_session(self) -> Dict[str, Any]:
        """Start a training session with introduction."""
        import time
        self.session_start_time = time.time()

        objections = self.load_objection_library()
        self.objections_remaining = objections.copy()

        # Get customer profile
        profile = self.customer_profile

        # AI introduction - blank slate, no knowledge of why they're being called
        intro_prompt = f"""You are a regular person who just received a phone call from an unknown number.

ABOUT YOU:
- You're at home or at work, mildly busy
- Current mood: {profile['mood']}
- You have a spouse

CRITICAL INSTRUCTIONS:
- You have NO IDEA who is calling or why
- You just picked up the phone from an unknown number
- Respond naturally — just say "Hello?" or "Yeah?" or "Who's this?"
- Keep it to ONE short sentence
- Do NOT mention benefits, insurance, sponsors, or anything — you don't know what this call is about
- NEVER use stage directions like *pauses*, [thinking], --emphatically--, or (nervously)
- NEVER use asterisks, brackets, or dashes for actions or emotions
- Just speak naturally

Answer the phone."""

        # Use streaming for faster response
        ai_message = ""
        with self.client.messages.stream(
            model="claude-sonnet-4-5",  # Sonnet is faster than Opus
            max_tokens=150,
            messages=[{"role": "user", "content": intro_prompt}]
        ) as stream:
            for text in stream.text_stream:
                ai_message += text

        # Filter stage directions before storage/TTS
        ai_message = clean_text_for_speech(ai_message)

        self.conversation_history.append({
            "role": "ai",
            "content": ai_message,
            "phase": "intro"
        })

        self.current_phase = "objection_handling"

        return {
            "success": True,
            "ai_message": ai_message,
            "phase": "intro"
        }

    def process_agent_response(self, agent_text: str) -> Dict[str, Any]:
        """
        Process agent's response and generate next AI message.

        Args:
            agent_text: What the agent said

        Returns:
            Dictionary with AI response and evaluation
        """
        # FIX #3: Detect "end call" intent
        end_call_phrases = [
            "end call", "end the call", "end session", "end training",
            "stop call", "stop training", "finish call", "i'm done",
            "that's all", "goodbye", "bye"
        ]

        # Normalize and check for end intent
        normalized_text = agent_text.lower().strip()
        if any(phrase in normalized_text for phrase in end_call_phrases):
            # Record the agent's goodbye before ending
            self.conversation_history.append({
                "role": "agent",
                "content": agent_text,
                "phase": self.current_phase
            })
            # Force session to wrap up immediately
            return self._wrap_up()

        # Record agent's response
        self.conversation_history.append({
            "role": "agent",
            "content": agent_text,
            "phase": self.current_phase
        })

        # Check time-based backstop
        import time
        import logging
        logger = logging.getLogger(__name__)

        if self.session_start_time:
            elapsed = time.time() - self.session_start_time
            if elapsed > self.max_session_duration:
                logger.warning(f"⚠️ Session exceeded {self.max_session_duration/60} minutes, forcing wrap-up")
                return self._wrap_up()

        # Graduated objection thresholds
        objection_count = len(self.objections_presented)

        if objection_count >= 5:
            # Tier 3: Natural wrap-up with soft landing
            logger.info(f"✅ Reached 5 objections, natural conclusion")
            return self._wrap_up_soft_landing()

        elif objection_count >= 3:
            # Tier 2: Conclusion-ready mode
            logger.info(f"🔔 In conclusion-ready mode ({objection_count} objections)")
            return self._conclusion_ready_mode()

        elif self.objections_remaining:
            # Tier 1: Active engagement, present objection
            return self._present_objection(agent_text)

        else:
            # No objections left, continue conversation
            return self._continue_conversation(agent_text)

    def _present_objection(self, agent_text: str) -> Dict[str, Any]:
        """Present objection naturally based on context and character profile"""

        if not self.objections_remaining:
            return self._continue_conversation(agent_text)

        # Detect what the agent just revealed
        self._detect_agent_disclosures(agent_text)

        # Get next objection but present it naturally
        objection = self.objections_remaining.pop(0)
        self.objections_presented.append(objection)

        profile = self.customer_profile

        # Build context (more messages for better flow)
        conversation_context = "\n".join([
            f"{'Agent' if msg['role'] == 'agent' else 'Customer'}: {msg['content']}"
            for msg in self.conversation_history[-5:]
        ])

        # Replace [sponsor_relationship] placeholder in objection statement
        objection_statement = objection['statement'].replace('[sponsor_relationship]', profile['sponsor_relationship'])

        # Build disclosed profile (only what agent has revealed)
        disclosed_profile = self._build_disclosed_profile()

        # More natural prompt that integrates the objection theme
        prompt = f"""You are in a phone conversation. Here's what you know:

WHAT YOU KNOW:
{disclosed_profile}

IMPORTANT: You ONLY know what the caller has told you during this conversation. Do NOT reference any information the agent hasn't mentioned yet. If they haven't explained why they're calling, you should still be confused about the purpose of this call.

RECENT CONVERSATION:
{conversation_context}

AGENT JUST SAID: "{agent_text}"

You have a concern about {objection['type']}. Based on what the agent just said and the conversation so far, naturally express this concern. The concern should feel like it emerges from the conversation, not like you're reading from a script.

Theme of your concern: {objection_statement}

Express this concern in a way that:
1. Responds to what the agent actually said
2. Sounds like a real person's natural skepticism or confusion
3. Fits the flow of the conversation
4. Matches your mood
5. Use casual language, filler words OK ("um", "well", "I mean")

Keep it to 1-2 sentences. Be a REAL PERSON.

CRITICAL: Do NOT use any stage directions or formatting:
- NO asterisks: *pauses*, *thinks*
- NO brackets: [aside], [thinking]
- NO dashes for emphasis: --emphatically--
- NO parenthetical actions: (nervously)
Just speak naturally. Your words should convey emotion, not markers.

Your response:"""

        # Use streaming for faster response
        ai_message = ""
        with self.client.messages.stream(
            model="claude-sonnet-4-5",
            max_tokens=150,
            messages=[{"role": "user", "content": prompt}]
        ) as stream:
            for text in stream.text_stream:
                ai_message += text

        # Filter stage directions before storage/TTS
        ai_message = clean_text_for_speech(ai_message)

        # Update profile
        self._update_profile_from_conversation(agent_text, ai_message)
        self.customer_profile['objections_raised'].append(objection['type'])

        self.conversation_history.append({
            "role": "ai",
            "content": ai_message,
            "phase": "objection_handling",
            "objection": objection
        })

        return {
            "success": True,
            "ai_message": ai_message,
            "phase": "objection_handling",
            "objection_type": objection["type"]
        }

    def _continue_conversation(self, agent_text: str) -> Dict[str, Any]:
        """Generate natural response based on agent's message and customer profile"""

        # Detect what the agent just revealed
        self._detect_agent_disclosures(agent_text)

        profile = self.customer_profile

        # Build comprehensive context (more messages for better memory)
        conversation_context = "\n".join([
            f"{'Agent' if msg['role'] == 'agent' else 'Customer'}: {msg['content']}"
            for msg in self.conversation_history[-5:]  # Last 5 messages for better context
        ])

        # Build disclosed profile (only what agent has revealed)
        disclosed_profile = self._build_disclosed_profile()

        prompt = f"""You are continuing a phone conversation. Here's what you know:

WHAT YOU KNOW:
{disclosed_profile}
- Topics discussed so far: {', '.join(profile['mentioned_topics']) if profile['mentioned_topics'] else 'nothing yet'}
- Concerns you've already raised: {', '.join(profile['objections_raised']) if profile['objections_raised'] else 'none yet'}

IMPORTANT: You ONLY know what the caller has told you during this conversation. Do NOT reference any information the agent hasn't mentioned yet.

RECENT CONVERSATION:
{conversation_context}

THE AGENT JUST SAID: "{agent_text}"

Respond naturally. Consider:
- Does what the agent said trigger any concerns? → Express them naturally
- Did the agent answer a previous question? → Acknowledge and continue
- Is something confusing or contradictory? → Ask for clarification
- Does this feel like a sales pitch? → Express skepticism if it fits your mood
- Is the agent being helpful and clear? → Be receptive and engaged

BE A REAL PERSON. Your response should flow naturally from what the agent just said.
Keep it to 1-2 sentences. Use casual language.

CRITICAL: Do NOT use any stage directions or formatting:
- NO asterisks: *pauses*, *thinks*
- NO brackets: [aside], [thinking]
- NO dashes for emphasis: --emphatically--
- NO parenthetical actions: (nervously)
Just speak naturally. Your words should convey emotion, not markers.

Your response:"""

        # Use streaming for faster response
        ai_message = ""
        with self.client.messages.stream(
            model="claude-sonnet-4-5",
            max_tokens=150,
            messages=[{"role": "user", "content": prompt}]
        ) as stream:
            for text in stream.text_stream:
                ai_message += text

        # Filter stage directions before storage/TTS
        ai_message = clean_text_for_speech(ai_message)

        # Update profile tracking
        self._update_profile_from_conversation(agent_text, ai_message)

        self.conversation_history.append({
            "role": "ai",
            "content": ai_message,
            "phase": "conversation"
        })

        return {
            "success": True,
            "ai_message": ai_message,
            "phase": "conversation"
        }

    def _update_profile_from_conversation(self, agent_text: str, ai_response: str):
        """Update customer profile based on conversation"""

        # Track topics mentioned by agent
        topics_map = {
            'cost': ['free', 'cost', 'pay', 'charge', 'money', 'price', 'dollar'],
            'time': ['schedule', 'appointment', 'meeting', 'time', 'minutes', 'hour', 'when'],
            'coverage': ['benefit', 'coverage', 'insurance', 'what do you get', 'plan', 'policy'],
            'trust': ['company', 'who are you', 'scam', 'legit', 'trust', 'verify']
        }

        for topic, keywords in topics_map.items():
            if any(keyword in agent_text.lower() for keyword in keywords):
                if topic not in self.customer_profile['mentioned_topics']:
                    self.customer_profile['mentioned_topics'].append(topic)

        # Track objections raised (simple detection based on question marks and concern keywords)
        objection_indicators = [
            ('?', 'how'), ('but', 'wait'), ('don\'t', 'understand'),
            ('catch', 'what'), ('scam', 'trust'), ('time', 'busy'),
            ('money', '?'), ('cost', '?')
        ]

        ai_lower = ai_response.lower()
        for indicator in objection_indicators:
            if all(word in ai_lower for word in indicator):
                # Classify objection type based on what was mentioned
                if 'cost' in self.customer_profile['mentioned_topics'] and 'cost' not in self.customer_profile['objections_raised']:
                    self.customer_profile['objections_raised'].append('cost')
                elif 'time' in self.customer_profile['mentioned_topics'] and 'time' not in self.customer_profile['objections_raised']:
                    self.customer_profile['objections_raised'].append('time')
                elif 'trust' in self.customer_profile['mentioned_topics'] and 'trust' not in self.customer_profile['objections_raised']:
                    self.customer_profile['objections_raised'].append('trust')

    def _conclusion_ready_mode(self) -> Dict[str, Any]:
        """
        AI is ready to conclude but doesn't force it.
        Responds naturally while signaling openness to ending.
        """
        conversation_context = "\n".join([
            f"{msg['role'].upper()}: {msg['content']}"
            for msg in self.conversation_history[-4:]
        ])

        prompt = f"""You are a person in a phone call. The caller has been explaining something to you.

CONVERSATION SO FAR:
{conversation_context}

CONTEXT:
- You've already raised {len(self.objections_presented)} concerns during this call
- The caller has addressed your concerns
- You're becoming more comfortable but haven't fully committed yet

INSTRUCTIONS:
- Respond naturally to what the caller just said
- Show that you're receptive and considering it
- Be positive and agreeable ("That makes sense", "I appreciate that", "Okay, I see")
- Don't raise NEW objections — you've already asked your questions
- If the caller offers next steps (text, appointment), acknowledge positively
- Keep it brief (1-2 sentences)

CRITICAL: Do NOT use any stage directions or formatting:
- NO asterisks: *pauses*, *thinks*
- NO brackets: [aside], [thinking]
- NO dashes for emphasis: --emphatically--
- NO parenthetical actions: (nervously)
Just speak naturally. Your words should convey emotion, not markers.

Your response (conversational, positive, brief):"""

        # Use streaming for faster response
        ai_message = ""
        with self.client.messages.stream(
            model="claude-sonnet-4-5",
            max_tokens=150,
            messages=[{"role": "user", "content": prompt}]
        ) as stream:
            for text in stream.text_stream:
                ai_message += text

        # Filter stage directions before storage/TTS
        ai_message = clean_text_for_speech(ai_message)

        self.conversation_history.append({
            "role": "ai",
            "content": ai_message,
            "phase": "conclusion_ready"
        })

        return {
            "success": True,
            "ai_message": ai_message,
            "phase": "conclusion_ready",
            "session_complete": False  # Don't end yet
        }

    def _wrap_up_soft_landing(self) -> Dict[str, Any]:
        """
        Conclude with a soft landing — customer naturally decides to move forward.
        Not abrupt, feels organic.
        """
        self.current_phase = "wrap_up"

        prompt = f"""You are a Plus Lead ending a phone call with benefits enrollment agent {self.agent_name}.

The agent has addressed {len(self.objections_presented)} of your concerns during this call. You're satisfied enough to move forward.

Generate a natural conclusion where YOU (the customer) make the decision to proceed:
- "Alright, I'm comfortable with this. Send me that text message."
- "Okay, you've answered my questions. Let's go ahead."
- "That sounds good. I'll look out for your text."

IMPORTANT:
- Sound like YOU decided, not like you're being forced
- Be brief (1-2 sentences)
- Accept the next steps the agent outlined
- Don't add new objections
- Sound natural and conversational

CRITICAL: Do NOT use any stage directions or formatting:
- NO asterisks: *pauses*, *thinks*
- NO brackets: [aside], [thinking]
- NO dashes for emphasis: --emphatically--
- NO parenthetical actions: (nervously)
Just speak naturally. Your words should convey emotion, not markers.

Your response:"""

        # Use streaming for faster response
        ai_message = ""
        with self.client.messages.stream(
            model="claude-sonnet-4-5",
            max_tokens=100,
            messages=[{"role": "user", "content": prompt}]
        ) as stream:
            for text in stream.text_stream:
                ai_message += text

        # Filter stage directions before storage/TTS
        ai_message = clean_text_for_speech(ai_message)

        self.conversation_history.append({
            "role": "ai",
            "content": ai_message,
            "phase": "wrap_up"
        })

        return {
            "success": True,
            "ai_message": ai_message,
            "phase": "wrap_up",
            "session_complete": True,
            "objections_presented": self.objections_presented
        }

    def _wrap_up(self) -> Dict[str, Any]:
        """Conclude the training session."""
        self.current_phase = "wrap_up"

        prompt = f"""You are a Plus Lead wrapping up a phone call with benefits enrollment agent {self.agent_name}.

The agent has walked you through their script and you've raised concerns during the call.

End the call naturally as a real person would:
- If the agent handled objections well, agree to the appointment or say you'll check the text
- If the agent was pushy or didn't address your concerns, be more hesitant ("I'll think about it")
- Keep it brief and natural (1-2 sentences)
- Don't be overly polite — sound like a normal person ending a call

CRITICAL: Do NOT use any stage directions or formatting:
- NO asterisks: *pauses*, *thinks*
- NO brackets: [aside], [thinking]
- NO dashes for emphasis: --emphatically--
- NO parenthetical actions: (nervously)
Just speak naturally. Your words should convey emotion, not markers."""

        # Use streaming for faster response
        ai_message = ""
        with self.client.messages.stream(
            model="claude-sonnet-4-5",
            max_tokens=100,
            messages=[{"role": "user", "content": prompt}]
        ) as stream:
            for text in stream.text_stream:
                ai_message += text

        # Filter stage directions before storage/TTS
        ai_message = clean_text_for_speech(ai_message)

        self.conversation_history.append({
            "role": "ai",
            "content": ai_message,
            "phase": "wrap_up"
        })

        return {
            "success": True,
            "ai_message": ai_message,
            "phase": "wrap_up",
            "session_complete": True
        }

    def get_conversation_transcript(self) -> List[Dict]:
        """Return full conversation history."""
        return self.conversation_history

if __name__ == "__main__":
    # Test conversation
    conv = TrainingConversation("Test Agent", "beginner")

    # Start session
    intro = conv.start_session()
    print(f"AI: {intro['ai_message']}\n")

    # Simulate agent response
    agent_response = "Hi Alex! Thanks for your interest. I'd love to tell you about our comprehensive coverage options..."
    result = conv.process_agent_response(agent_response)
    print(f"Agent: {agent_response}")
    print(f"AI: {result['ai_message']}\n")

    # Simulate another agent response
    agent_response_2 = "I understand your concern about price. Let me explain the value you're getting for $150/month..."
    result2 = conv.process_agent_response(agent_response_2)
    print(f"Agent: {agent_response_2}")
    print(f"AI: {result2['ai_message']}\n")

    print("✓ Conversation manager test complete")
