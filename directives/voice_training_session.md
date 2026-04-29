# Directive: Voice Training Session

## Purpose
Orchestrate a realistic voice-based training session where insurance agents practice handling customer objections. The AI simulates a potential customer presenting objections, evaluates the agent's responses, and provides a performance score.

## Inputs
- `agent_name`: Name of the agent being trained (required)
- `session_type`: Type of training ("objection_handling", "full_pitch", "quick_practice") (default: "objection_handling")
- `duration_minutes`: Target session length (default: 10)
- `difficulty_level`: "beginner", "intermediate", "advanced" (default: "intermediate")

## Tools
- `execution/web_voice_server.py` - Serves web interface and manages WebSocket connections
- `execution/transcribe_audio.py` - Converts agent's speech to text in real-time
- `execution/synthesize_speech.py` - Generates AI voice responses
- `execution/conversation_manager.py` - Manages conversation flow using Claude API
- `execution/score_response.py` - Evaluates agent responses against objection library
- `execution/save_training_session.py` - Logs session data to Google Sheets

## Process

### 1. Session Initialization
- Agent opens web interface and clicks "Start Training Session"
- System prompts for agent name and session preferences
- Microphone permission requested and verified
- WebSocket connection established for real-time audio streaming

### 2. Introduction Phase (30 seconds)
- AI introduces itself: "Hi, my name is [Customer Name]. I received your information about insurance coverage..."
- Agent responds with their opening script
- System begins transcribing and evaluating from first response

### 3. Objection Handling Phase (7-9 minutes)
- AI presents 3-5 objections based on `difficulty_level`:
  - **Beginner**: Price objection, "I need to think about it"
  - **Intermediate**: Coverage concerns, competitor comparison
  - **Advanced**: Complex scenarios, multiple objections combined

- For each objection:
  1. AI presents objection naturally in conversation
  2. Agent responds (transcription active)
  3. System checks response against objection library using `score_response.py`
  4. If response is inadequate, AI may probe further or present follow-up
  5. If response is good, AI moves to next objection

- Conversation flows naturally (not robotic back-and-forth)
- AI adapts based on agent's performance

### 4. Wrap-up Phase (30 seconds)
- AI concludes: "Thank you for the information. I'll think about it and get back to you."
- Agent closes the call appropriately

### 5. Feedback Phase (1-2 minutes)
- Voice feedback: "Your session is complete. Your score is [X]/10."
- Detailed scoring breakdown displayed on screen
- Specific praise for what went well
- Specific areas for improvement with examples
- Transcript shown with highlights (correct responses in green, missed opportunities in yellow)

### 6. Data Logging
- Complete session saved to Google Sheets:
  - Agent name, timestamp, duration
  - Score breakdown by category
  - Objections presented and responses given
  - Full transcript
  - Areas for improvement

- Slack notification sent to trainer channel if score < 7.0 (needs follow-up)

## Outputs
- **Primary**: Real-time voice conversation with performance evaluation
- **Google Sheet**: "Training Sessions" log with detailed metrics
- **Slack**: Notifications for low scores or system errors
- **Agent Display**: On-screen score, feedback, and transcript

## Edge Cases

### Audio Quality Issues
- If transcription confidence < 60%, ask agent to repeat
- If persistent issues, suggest checking microphone or connection
- Log audio quality metrics for troubleshooting

### Agent Goes Off-Script Significantly
- If agent uses inappropriate language or approach, gently redirect
- AI should stay in character but guide back to proper technique
- Flag in scoring if major script violations occur

### Technical Interruptions
- If WebSocket disconnects, attempt auto-reconnect (3 tries)
- If session crashes mid-way, offer to resume or restart
- Save partial session data to prevent data loss

### Time Limits
- If session exceeds `duration_minutes` + 2, AI should naturally conclude
- Don't cut off mid-objection; find natural stopping point

### Difficult Objections Handling
- If agent struggles with same objection 2+ times, AI moves on
- Note in feedback that this objection needs additional training
- Trainer notified via Slack for one-on-one follow-up

## Success Criteria
- [x] Agent completes full session without technical issues
- [x] At least 3 objections presented and handled
- [x] Responses evaluated against company-approved objection library
- [x] Score calculated using standardized rubric (see `score_performance.md`)
- [x] Session data logged to Google Sheets within 30 seconds of completion
- [x] Feedback provided to agent (voice + visual)
- [x] Trainer notified if intervention needed

## Performance Targets
- **Response Time**: AI voice response within 1-2 seconds of agent finishing
- **Transcription Accuracy**: >90% word accuracy
- **Session Completion Rate**: >95% of sessions complete successfully
- **User Satisfaction**: Agents rate experience 4+ stars out of 5

## Notes
- The AI should sound natural and conversational, not robotic
- Personality should be friendly but realistic (mix of interested/skeptical)
- Avoid making it too easy or too hard - balance is key
- Voice should vary (male/female, different ages) to simulate real customer diversity
- System should learn from patterns: if many agents struggle with specific objection, flag for trainer review

## Customer Persona System

### Dynamic Character Generation

Each training session generates a unique customer character with:
- **Sponsor relationship**: Sister, brother, mom, dad, friend, or cousin
- **Memory state**: 60% remember being sponsored, 40% forgot
- **Mood**: Curious, skeptical, busy, or confused
- **Pain points**: 2-3 concerns (time, cost, trust, coverage) based on difficulty level

The AI maintains this persona throughout the conversation, responding naturally based on what the agent says.

### Natural Objection Flow

Objections emerge organically when:
- Agent's words trigger one of the customer's pain points
- Customer's mood makes them skeptical
- Something doesn't make sense based on previous conversation
- Customer remembers/forgets being sponsored ("Wait, did my sister mention this?")

This creates realistic practice where agents can't predict exact objection timing or wording.

### Conversation Memory

The AI tracks:
- **Topics discussed**: Cost, time, coverage, trust
- **Objections already raised**: Prevents repeating the same concern
- **Key facts learned**: What the agent has explained
- **Sponsor details**: Consistently refers to the same family member throughout

This ensures the conversation flows naturally like a real phone call, with the AI remembering what was said earlier.

### Benefits

- **More realistic training**: Feels like talking to a real person, not following a script
- **Context-aware responses**: AI responds to what the agent actually says
- **Natural objection emergence**: Concerns arise from the conversation, not forced
- **Consistent character**: Customer personality remains stable throughout the session
- **Memory gaps feel authentic**: "I don't remember my mom mentioning this..." sounds natural

## Text Filtering System

### Purpose
Prevents stage directions and formatting markers from being read aloud by text-to-speech engines, ensuring natural-sounding AI voice responses.

### Problem Solved
AI models sometimes generate responses with theatrical formatting like `*pauses*`, `[thinking]`, `--emphatically--`, or `(nervously)`. Without filtering, TTS engines read these verbatim ("asterisk pauses asterisk"), breaking immersion and making the AI sound robotic.

### Filtered Patterns
The system automatically removes:
- `*action*` - Asterisk-wrapped actions (e.g., `*pauses*`, `*thinking*`, `*nervous laugh*`)
- `[aside]` - Bracketed stage directions (e.g., `[thinking]`, `[pauses to think]`)
- `--emotion--` - Dashed emphasis markers (e.g., `--emphatically--`, `--softly--`)
- `(nervously)` - Parenthetical emotions (adverbs only, at sentence start or mid-sentence)

### Preserved Patterns
The system intelligently preserves:
- Legitimate parentheses: "We offer benefits (life, health, and dental)"
- Hyphens in compound words: "sister-in-law"
- Number ranges: "2-3 weeks"
- Math expressions: "$25-30 per month"

### Architecture (Three-Layer Defense)

1. **Prompt Engineering** - Explicit instructions in AI prompts forbidding stage directions
   - Location: `execution/conversation_manager.py` (4 prompts updated)
   - First line of defense: prevents generation at the source

2. **Post-Generation Filtering** - Automatic removal after AI generates responses
   - Location: `execution/conversation_manager.py` (4 filter calls)
   - Second line of defense: catches any markers that slip through

3. **Pre-TTS Safety Filter** - Final check before audio synthesis
   - Location: `execution/synthesize_speech.py` (Google TTS & ElevenLabs)
   - Third line of defense: ensures no markers reach the TTS engine

### Implementation Details

**Core Filter:** `execution/text_filters.py`
- Uses regex patterns to identify and remove stage directions
- Preserves legitimate punctuation and speech patterns
- Logs filtered content for debugging and monitoring

**Testing:** `execution/test_text_filters.py`
- Comprehensive test suite with 20+ test cases
- Run with: `pytest execution/test_text_filters.py -v`
- Validates edge cases and preserves legitimate text

### Monitoring

**Log Messages:**
- Look for `🧹 Filtered stage directions from text` in server logs
- Indicates when filtering occurred and what was removed
- If filtering happens frequently (>10% of responses), review and improve prompts

**Action Threshold:**
- If >10% of responses require filtering, the prompts may need refinement
- Goal: Prevent stage directions at the source through better prompt engineering
- Filtering should be a safety net, not the primary solution

### Testing

**Unit Tests:**
```bash
cd execution/
pytest test_text_filters.py -v
```

**Integration Test:**
1. Start voice server: `python3 execution/web_voice_server.py`
2. Open browser to `http://localhost:5001`
3. Start a training session
4. Monitor logs for filter activity
5. Listen to AI responses - should be natural with no stage directions

### Success Metrics

**Before Implementation:**
- Stage directions occasionally appear in AI responses
- TTS reads formatting markers verbatim
- Breaks immersion and sounds robotic

**After Implementation:**
- Zero stage directions in audio output
- Natural conversational flow preserved
- No legitimate speech content removed
- No performance degradation in TTS latency
