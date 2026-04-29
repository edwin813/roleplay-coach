# Directive: Score Performance

## Purpose
Define the standardized scoring rubric for evaluating agent performance during voice training sessions. This ensures consistent, objective assessment across all training sessions.

## Overall Score Calculation

**Final Score = Weighted Average of 5 Categories (0-10 scale)**

Categories:
1. **Objection Handling** (40% weight) - Correctness of responses
2. **Tone & Confidence** (20% weight) - Voice quality and assurance
3. **Script Adherence** (15% weight) - Following company script
4. **Active Listening** (15% weight) - Responding to customer cues
5. **Professionalism** (10% weight) - Overall conduct

---

## Category 1: Objection Handling (40% weight)

**What It Measures**: How well the agent handles customer objections using company-approved responses.

**Scoring Method**:
- Each objection is scored individually using `objection_library.md`
- Average all objection scores for category score
- Example: Agent faces 4 objections, scores [8, 10, 6, 9] → Average = 8.25/10

**Score Breakdown**:
- **9-10**: Exceptional - Hits all key points, natural delivery, builds rapport
- **7-8**: Good - Covers main points, minor gaps, professional
- **5-6**: Needs Improvement - Misses key elements, sounds scripted, doesn't connect
- **3-4**: Poor - Misses most points, incorrect approach, defensive
- **0-2**: Failing - No proper objection handling, inappropriate responses

---

## Category 2: Tone & Confidence (20% weight)

**What It Measures**: Voice quality, confidence level, and speaking style.

**Evaluation Criteria**:
- **Voice Clarity**: Easy to understand, good volume, minimal filler words
- **Confidence Level**: Sounds assured (not hesitant or overly aggressive)
- **Pace**: Appropriate speed (not too fast or too slow)
- **Energy**: Engaged and enthusiastic (not monotone or over-excited)

**Scoring Method**:
- AI analyzes speech patterns, tone, pace throughout conversation
- Human-like assessment: "Would I trust this person?"

**Score Breakdown**:
- **9-10**: Excellent tone - Confident, warm, professional, trustworthy
- **7-8**: Good tone - Mostly confident, occasional hesitation, professional
- **5-6**: Inconsistent - Wavers between confident and uncertain, some nervous habits
- **3-4**: Weak - Sounds unsure, too quiet/loud, poor pacing, many filler words
- **0-2**: Poor - No confidence, inappropriate tone, hard to understand

**Red Flags** (automatic point deduction):
- Excessive "um," "uh," "like" (more than 5 per minute): -1 point
- Speaking too fast (nervous): -1 point
- Long awkward pauses (>5 seconds): -0.5 points each
- Sounding robotic/reading script: -2 points

---

## Category 3: Script Adherence (15% weight)

**What It Measures**: How well the agent follows the company-approved phone script.

**Required Script Elements** (Plus Lead Phone Script):
1. **Opening**: Introduces self by name, references sponsor by name and relationship
2. **Text Reference**: Asks if lead saw the text about benefits package
3. **Sponsor Credibility**: Mentions sponsor is a member in good standing, extended benefits to lead
4. **Information Verification**: Confirms lead's city/area and spouse name
5. **Benefits Activation**: Explains need to activate benefits, asks about device (laptop/tablet/phone)
6. **Commitment Close**: If scheduling, gives two time options on same day, asks for "CONFIRM" text back

**Scoring Method**:
- Check if each required element is present
- 6 elements: Opening (2pts), Text Reference (1.5pts), Sponsor Credibility (2pts), Info Verification (1.5pts), Benefits Activation (1.5pts), Commitment Close (1.5pts) = 10 total
- Deduct points for going completely off-script

**Score Breakdown**:
- **9-10**: Follows script perfectly while sounding natural
- **7-8**: Hits all major script points, minor deviations
- **5-6**: Misses 1-2 script elements, or sounds too robotic
- **3-4**: Misses several script elements, significant deviations
- **0-2**: Ignores script entirely, inappropriate approach

---

## Category 4: Active Listening (15% weight)

**What It Measures**: Agent's ability to respond appropriately to customer cues and adapt conversation.

**Evaluation Criteria**:
- **Acknowledgment**: Responds to what customer says (not just waiting to talk)
- **Adaptation**: Adjusts approach based on customer's tone/concerns
- **Relevant Responses**: Answers actual questions (doesn't give canned responses)
- **Builds on Information**: References earlier parts of conversation

**Scoring Method**:
- AI tracks if agent responds to specific customer statements
- Example: Customer mentions "I have kids" → Good agent connects to family protection benefits

**Score Breakdown**:
- **9-10**: Exceptional listening - References customer's words, adapts perfectly, builds rapport
- **7-8**: Good listening - Acknowledges points, mostly relevant responses
- **5-6**: Inconsistent - Sometimes listens, sometimes gives generic responses
- **3-4**: Poor listening - Canned responses, doesn't acknowledge customer concerns
- **0-2**: Not listening - Talks over customer, completely ignores what they say

**Examples**:
- **Good** (10 points): Customer: "I'm worried about my kids' future." Agent: "I completely understand - protecting your children's future is exactly why this coverage is so important. Tell me more about your family..."
- **Bad** (2 points): Customer: "I'm worried about my kids' future." Agent: "This policy has great benefits and affordable rates..."

---

## Category 5: Professionalism (10% weight)

**What It Measures**: Overall professional conduct and etiquette.

**Evaluation Criteria**:
- **Respectful Language**: No slang, inappropriate words, or unprofessional phrases
- **Customer-Centric**: Focuses on customer's needs (not pushy about sale)
- **Patience**: Handles objections without frustration
- **Courtesy**: Says "please," "thank you," shows appreciation

**Scoring Method**:
- Starts at 10/10
- Deductions for unprofessional behavior

**Deductions**:
- Interrupting customer: -2 points
- Dismissive language ("That's not a big deal"): -3 points
- Pushy/aggressive tone: -3 points
- Inappropriate language: -5 points
- Ending call abruptly: -2 points

**Score Breakdown**:
- **9-10**: Highly professional throughout
- **7-8**: Professional with minor lapses
- **5-6**: Some unprofessional moments
- **3-4**: Multiple professional issues
- **0-2**: Unprofessional conduct

---

## Final Score Calculation Example

**Session Details**:
- 4 objections presented: Scores [8, 10, 7, 9] → Average: 8.5/10
- Tone & Confidence: 7/10
- Script Adherence: 9/10
- Active Listening: 8/10
- Professionalism: 10/10

**Calculation**:
```
Final Score = (8.5 × 0.40) + (7 × 0.20) + (9 × 0.15) + (8 × 0.15) + (10 × 0.10)
            = 3.4 + 1.4 + 1.35 + 1.2 + 1.0
            = 8.35/10
```

**Rounded Final Score**: **8.4/10**

---

## Score Interpretation

**9.0 - 10.0**: 🌟 **Excellent** - Ready for live calls
**7.0 - 8.9**: ✅ **Good** - Minor improvements needed
**5.0 - 6.9**: ⚠️ **Needs Work** - Requires additional training
**Below 5.0**: ❌ **Not Ready** - Significant training needed, trainer follow-up required

---

## Feedback Templates

Based on score, provide specific feedback:

### Excellent (9.0-10.0)
"Outstanding performance! You demonstrated strong objection handling, excellent tone, and professional conduct throughout. You're ready to handle live calls. Keep up the great work!"

### Good (7.0-8.9)
"Great job! You handled most objections well and maintained professionalism. Focus on [specific area] to reach the next level. [Specific tip based on lowest category score]."

### Needs Work (5.0-6.9)
"You're making progress, but there are key areas to improve. Focus on: [list 2-3 specific improvements]. I recommend practicing [specific objection] and reviewing the script for [specific section]. Let's schedule a follow-up session with your trainer."

### Not Ready (Below 5.0)
"This session showed areas that need significant improvement. Your trainer will be notified for one-on-one coaching. Focus on: [specific issues]. Keep practicing - you'll get there!"

---

## Automatic Alerts

**Trigger Slack notification to trainer if**:
- Overall score < 7.0
- Any category score < 5.0
- Same objection failed multiple sessions in a row
- Professionalism score < 8.0 (conduct issue)

---

## Usage Notes

- Scores should be calculated immediately after session ends
- Provide both numerical score and qualitative feedback
- Track scores over time to show improvement
- Adjust difficulty level based on consistent performance (if agent scores 9+ consistently, move to advanced)
- Update rubric as company standards evolve
