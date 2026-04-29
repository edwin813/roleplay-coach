# 🎙️ Voice Training Platform - Quick Start

## What You Just Built

A **complete web-based voice training system** for insurance sales agents that:

✅ Simulates realistic customer conversations with AI
✅ Presents company objections via voice
✅ Scores agent responses automatically (0-10 scale)
✅ Provides detailed feedback on performance
✅ Logs sessions to Google Sheets
✅ Notifies trainers when agents need help

## 🚀 Get Started in 3 Steps

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Add Your Anthropic API Key
```bash
cp .env.template .env
# Edit .env and add: ANTHROPIC_API_KEY=sk-ant-...
```

### 3. Start Training!
```bash
cd execution
python web_voice_server.py
# Open: http://localhost:5000
```

That's it! The system works with just Claude API. Everything else is optional.

---

## 📁 What Was Built

### Layer 1: Directives (What to Do)
```
directives/
├── voice_training_session.md  - Training flow & session structure
├── objection_library.md        - Company objections & correct responses
└── score_performance.md        - Scoring rubric (0-10 scale)
```

### Layer 2: AI Orchestration (You)
Claude reads directives, manages conversations, scores responses, learns from patterns.

### Layer 3: Execution Scripts (Doing the Work)
```
execution/
├── web_voice_server.py         - Flask web server + WebSocket
├── conversation_manager.py     - AI conversation orchestration
├── score_response.py           - Performance evaluation
├── transcribe_audio.py         - Speech-to-text (Deepgram or browser)
├── synthesize_speech.py        - Text-to-speech (Google/ElevenLabs)
└── save_training_session.py    - Google Sheets + Slack logging
```

### Web Interface
```
web/
├── templates/
│   └── index.html              - Main training interface
├── static/
│   ├── css/style.css           - Beautiful gradient UI
│   └── js/app.js               - WebSocket client & voice handling
```

---

## 🎯 Next Steps

### 1. Customize Objections (IMPORTANT)
Edit [directives/objection_library.md](directives/objection_library.md) and replace the sample objections with your actual company-approved objection responses.

**Current samples:**
- Price objection ("Too expensive")
- Timing objection ("Need to think about it")
- Coverage objection ("Already have insurance")
- Trust objection ("Don't trust insurance companies")
- Competitor comparison

**Replace with YOUR scenarios!**

### 2. Test It Yourself
1. Open http://localhost:5000
2. Enter your name
3. Complete a beginner training session
4. See how the scoring works

### 3. Add Voice (Optional but Recommended)
**Free option:** Works automatically in Chrome/Edge (Web Speech API)

**Better option:** Add Deepgram for transcription
```bash
# Get API key from https://console.deepgram.com/
# Add to .env: DEEPGRAM_API_KEY=...
```

### 4. Set Up Logging (Optional)
**Google Sheets:**
1. Create a Google Sheet
2. Add headers (see [SETUP_VOICE_TRAINING.md](SETUP_VOICE_TRAINING.md))
3. Get spreadsheet ID
4. Add to .env: `GOOGLE_SHEETS_TRAINING_LOG_ID=...`

**Slack Notifications:**
1. Create Incoming Webhook
2. Add to .env: `SLACK_WEBHOOK_URL=...`

---

## 💡 How It Works

### The 3-Layer Architecture

**When an agent starts training:**

1. **Browser** → Agent clicks "Start Training"
2. **WebSocket** → Connects to Flask server
3. **Conversation Manager** → Claude AI creates customer personality
4. **Speech Synthesis** → Converts AI text to voice
5. **Agent speaks** → Browser captures audio
6. **Transcription** → Speech-to-text conversion
7. **Scoring** → Claude evaluates response against objection library
8. **Next Objection** → AI presents next scenario
9. **Final Score** → Calculate weighted performance score
10. **Logging** → Save to Google Sheets, notify Slack if needed

### Scoring Breakdown (from `score_performance.md`)

| Category | Weight |
|----------|--------|
| Objection Handling | 40% |
| Tone & Confidence | 20% |
| Script Adherence | 15% |
| Active Listening | 15% |
| Professionalism | 10% |

**Final Score = Weighted average of all categories (0-10 scale)**

- 9.0-10.0 = Excellent (ready for live calls)
- 7.0-8.9 = Good (minor improvements needed)
- 5.0-6.9 = Needs Work (additional training required)
- < 5.0 = Not Ready (trainer follow-up needed)

---

## 📊 Cost Estimate

**Minimal Setup (Claude only):**
- ~$0.15 per 10-minute session
- 100 agents × 2 sessions/week = $30/week = **$120/month**

**Full Setup (with voice):**
- ~$0.25 per 10-minute session
- 100 agents × 2 sessions/week = $50/week = **$200/month**

**Compare to:** Manual training time = hours per week per trainer!

---

## 🔧 Customization Points

### 1. Objection Library
[directives/objection_library.md](directives/objection_library.md) - Your objections, your responses, your scoring

### 2. Scoring Rubric
[directives/score_performance.md](directives/score_performance.md) - Adjust weights, categories, feedback templates

### 3. Session Flow
[directives/voice_training_session.md](directives/voice_training_session.md) - Change session length, number of objections, phases

### 4. Voice Settings
[execution/synthesize_speech.py](execution/synthesize_speech.py):59 - Change AI voice (male/female, accent, tone)

### 5. UI/UX
- [web/templates/index.html](web/templates/index.html) - Interface structure
- [web/static/css/style.css](web/static/css/style.css) - Colors, layout, styling
- [web/static/js/app.js](web/static/js/app.js) - Behavior, logic

---

## 🎓 Usage Tips

### For Trainers:
- Start with **beginner** difficulty for new agents
- Review Google Sheets logs weekly
- Update objection library based on patterns
- Adjust scoring weights if needed
- Use Slack notifications to identify struggling agents

### For Agents:
- Treat it like a real call (not a test!)
- Use a **quiet environment**
- Speak clearly and naturally
- Actually **listen** to the AI customer
- Review feedback after each session
- Practice the objections you scored lowest on

---

## 📖 Full Documentation

- [SETUP_VOICE_TRAINING.md](SETUP_VOICE_TRAINING.md) - Complete setup guide
- [README.md](README.md) - Architecture overview
- [CLAUDE.md](CLAUDE.md) - Agent instructions

---

## 🐛 Troubleshooting

**"Server won't start"**
```bash
# Check if port 5000 is in use
lsof -i :5000
# Use different port if needed
```

**"AI not responding"**
- Check `.env` has `ANTHROPIC_API_KEY=sk-ant-...`
- Verify API key is valid
- Check console for errors (F12)

**"Microphone not working"**
- Allow microphone permission in browser
- Try Chrome (best support)
- Check system microphone settings

**"Poor voice quality"**
- Add Deepgram API key for better transcription
- Use ElevenLabs for better voice synthesis
- Check microphone quality

**See [SETUP_VOICE_TRAINING.md](SETUP_VOICE_TRAINING.md) for more**

---

## 🎉 You're Ready!

1. ✅ **Customize objections** in `directives/objection_library.md`
2. ✅ **Start server:** `cd execution && python web_voice_server.py`
3. ✅ **Open browser:** http://localhost:5000
4. ✅ **Train!**

**Questions?** Check the [Setup Guide](SETUP_VOICE_TRAINING.md) or review the [directives/](directives/) folder for detailed configuration.

---

Built with the **3-Layer AI Architecture**
- Directives define the "what"
- AI orchestrates the "how"
- Scripts execute the "do"

**Happy Training!** 🎙️📈
