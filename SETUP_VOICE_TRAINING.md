# Voice Training Platform - Setup Guide

This guide will walk you through setting up the web-based voice training platform for insurance sales agents.

## Prerequisites

- Python 3.8 or higher
- Modern web browser (Chrome, Firefox, Safari, Edge)
- Microphone access
- Internet connection

## Quick Start (5 Minutes)

### 1. Install Dependencies

```bash
# Install Python packages
pip install -r requirements.txt
```

### 2. Configure API Keys

Copy the environment template:
```bash
cp .env.template .env
```

Edit `.env` and add your API keys:

**Required:**
- `ANTHROPIC_API_KEY` - Get from https://console.anthropic.com/

**Optional (but recommended):**
- `DEEPGRAM_API_KEY` - Get from https://console.deepgram.com/ (for better transcription)
- `GOOGLE_SHEETS_TRAINING_LOG_ID` - Your Google Sheet ID for logging

### 3. Customize Your Objections

Edit `directives/objection_library.md` and replace the sample objections with your company's actual objection scenarios and approved responses.

### 4. Start the Server

```bash
cd execution
python web_voice_server.py
```

You should see:
```
🎙️  Starting Voice Training Platform...
📍 Server running at: http://localhost:5000
🔌 WebSocket ready for connections
```

### 5. Open in Browser

Navigate to: **http://localhost:5000**

That's it! You're ready to train.

---

## Detailed Setup

### API Keys & Services

#### 1. Anthropic (REQUIRED)

The AI conversation engine requires Claude API access.

1. Go to https://console.anthropic.com/
2. Create an account or sign in
3. Navigate to API Keys
4. Create a new key
5. Add to `.env`: `ANTHROPIC_API_KEY=sk-ant-...`

**Cost:** ~$0.15 per 10-minute training session

#### 2. Speech Recognition (RECOMMENDED)

You have two options:

**Option A: Browser Web Speech API (FREE)**
- Works automatically in Chrome/Edge
- No API key needed
- Lower quality but free
- Limited browser support

**Option B: Deepgram (PAID, BETTER QUALITY)**
- More accurate transcription
- Works in all browsers
- Faster processing

Setup:
1. Go to https://console.deepgram.com/
2. Create account and get API key
3. Add to `.env`: `DEEPGRAM_API_KEY=...`

**Cost:** ~$0.05 per 10-minute session

#### 3. Text-to-Speech (RECOMMENDED)

**Option A: Google Cloud TTS**
1. Go to https://console.cloud.google.com/
2. Create project and enable Text-to-Speech API
3. Download `credentials.json` to project root
4. No .env entry needed

**Cost:** ~$0.05 per session

**Option B: ElevenLabs (BETTER QUALITY)**
1. Go to https://elevenlabs.io/
2. Get API key
3. Add to `.env`: `ELEVENLABS_API_KEY=...`

**Cost:** ~$0.05 per session

#### 4. Google Sheets Logging (OPTIONAL)

To save training sessions to Google Sheets:

1. Create a new Google Sheet
2. Name it "Insurance Training Sessions"
3. Add these headers to Row 1:
   ```
   Agent Name | Date/Time | Duration (minutes) | Final Score | Grade |
   Objections Handled | Objection Handling Score | Tone & Confidence Score |
   Script Adherence Score | Active Listening Score | Professionalism Score |
   Areas for Improvement | Transcript Link
   ```
4. Copy the spreadsheet ID from the URL:
   ```
   https://docs.google.com/spreadsheets/d/[THIS_IS_THE_ID]/edit
   ```
5. Add to `.env`: `GOOGLE_SHEETS_TRAINING_LOG_ID=...`
6. Share the sheet with your Google service account

#### 5. Slack Notifications (OPTIONAL)

Get notified when agents need follow-up:

1. Create a Slack Incoming Webhook: https://api.slack.com/messaging/webhooks
2. Add to `.env`: `SLACK_WEBHOOK_URL=https://hooks.slack.com/...`

Notifications sent when:
- Agent scores below 7.0
- Multiple attempts on same objection fail

---

## Customization

### 1. Update Objection Library

Edit `directives/objection_library.md`:

```markdown
## Objection X: Your Custom Objection

**Type**: price/timing/coverage/trust/competitor
**Difficulty**: beginner/intermediate/advanced
**Scoring Weight**: 1-10

**Customer Statement**:
"What the AI customer will say..."

**Correct Response Elements** (Agent must hit at least X of Y):
1. Key point the agent should make
2. Another important element
3. etc.

**Common Mistakes to Avoid**:
- Mistake 1
- Mistake 2

**Scoring**:
- Y/Y elements = 10 points
- (Y-1)/Y elements = 8 points
- etc.
```

### 2. Adjust Scoring Rubric

Edit `directives/score_performance.md` to change:
- Category weights (currently: 40% objection handling, 20% tone, etc.)
- Score breakdowns
- Feedback templates

### 3. Modify Training Flow

Edit `directives/voice_training_session.md` to adjust:
- Session length
- Number of objections
- Introduction script
- Wrap-up approach

### 4. Change Voice Settings

Edit `execution/synthesize_speech.py`:

```python
VOICE_PROFILES = {
    "google": {
        "female_friendly": "en-US-Neural2-A",  # Change these
        "male_professional": "en-US-Neural2-I",
    }
}
```

Available Google voices: https://cloud.google.com/text-to-speech/docs/voices

---

## Running the Platform

### Start Server

```bash
cd execution
python web_voice_server.py
```

Server runs on: **http://localhost:5000**

### For Production (External Access)

If you want agents to access from different computers:

1. **Option A: Run on server**
   ```bash
   # Install on a server
   python web_voice_server.py
   # Access via: http://your-server-ip:5000
   ```

2. **Option B: Use ngrok (Quick testing)**
   ```bash
   # In another terminal
   ngrok http 5000
   # Share the https://xxx.ngrok.io URL
   ```

3. **Option C: Deploy to cloud**
   - Deploy to Heroku, Railway, Render, etc.
   - Set environment variables in the platform
   - Use production WSGI server (gunicorn)

---

## Usage Guide for Agents

### Starting a Training Session

1. Open the platform URL in Chrome/Firefox/Safari
2. Enter your name
3. Select difficulty level:
   - **Beginner**: Basic price and timing objections
   - **Intermediate**: Coverage and competitor questions
   - **Advanced**: Trust issues and complex scenarios
4. Click "Start Training"
5. Allow microphone access when prompted

### During the Session

1. **Listen** to the AI customer
2. **Click the microphone** when ready to respond
3. **Speak** your response clearly
4. The AI will respond and present objections
5. Continue until session completes (3-5 objections)

### After the Session

- View your score (0-10 scale)
- Review category breakdowns
- Read specific feedback
- See full transcript
- Start a new session to practice more

### Tips for Best Results

✅ **DO:**
- Use a quiet environment
- Speak clearly and at normal pace
- Follow your company script
- Actually listen to the AI customer
- Treat it like a real call

❌ **DON'T:**
- Rush through responses
- Ignore what the customer says
- Use overly scripted/robotic language
- Get frustrated - it's practice!

---

## Troubleshooting

### "Microphone not working"
- Check browser permissions
- Ensure microphone is connected
- Try a different browser (Chrome works best)
- Check system microphone settings

### "AI not responding"
- Check console for errors (F12 in browser)
- Verify ANTHROPIC_API_KEY in .env
- Check server terminal for error messages
- Restart the server

### "Voice synthesis not working"
- Platform falls back to text-only mode
- Check Google credentials.json exists
- Or add ELEVENLABS_API_KEY
- Voice isn't required - text works too

### "Session not saving to Google Sheets"
- Check GOOGLE_SHEETS_TRAINING_LOG_ID is set
- Verify sheet is shared with service account
- Check credentials.json is valid
- Session still works, just won't log

### "Poor transcription quality"
- Use Deepgram API instead of browser (add DEEPGRAM_API_KEY)
- Improve microphone quality
- Reduce background noise
- Speak more clearly

---

## Architecture Overview

```
User (Browser)
    ↓
Web Interface (HTML/CSS/JS)
    ↓
WebSocket Connection
    ↓
Flask Server (web_voice_server.py)
    ↓
├── Conversation Manager (conversation_manager.py)
│   └── Claude API (AI responses)
├── Transcription (transcribe_audio.py)
│   └── Deepgram or Web Speech API
├── Speech Synthesis (synthesize_speech.py)
│   └── Google TTS or ElevenLabs
├── Scoring (score_response.py)
│   └── Claude API (evaluation)
└── Logging (save_training_session.py)
    ├── Google Sheets
    └── Slack notifications
```

---

## Cost Breakdown

Per 10-minute training session:

| Service | Cost | Required? |
|---------|------|-----------|
| Anthropic Claude | $0.15 | ✅ Required |
| Deepgram (transcription) | $0.05 | Optional (free browser alternative) |
| Google TTS | $0.05 | Optional (affects experience) |
| Google Sheets | Free | Optional |
| Slack | Free | Optional |
| **Total (full)** | **$0.25** | |
| **Total (minimal)** | **$0.15** | Claude only |

**For 100 agents doing 2 sessions/week:**
- Full setup: $50/week = $200/month
- Minimal setup: $30/week = $120/month

Much cheaper than manual training time!

---

## Next Steps

1. ✅ **Test the system yourself** - Complete a training session
2. ✅ **Customize objections** - Replace samples with your real scenarios
3. ✅ **Train one agent** - Get feedback on the experience
4. ✅ **Iterate** - Adjust scoring, difficulty, objections based on feedback
5. ✅ **Scale** - Roll out to full team

## Support

For issues or questions:
1. Check this guide's Troubleshooting section
2. Review the console logs (F12 in browser + server terminal)
3. Check `directives/` for configuration details

## License & Usage

This is part of your 3-layer AI architecture system. Customize freely for your training needs.

---

**🎉 You're all set! Happy training!**
