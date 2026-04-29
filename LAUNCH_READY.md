# 🎙️ Voice Training Platform - LAUNCH READY!

## ✅ SYSTEM STATUS: FULLY OPERATIONAL

Your insurance sales training platform is live and ready to use!

---

## 🌐 **Access Your Platform**

**URL:** **http://localhost:5001**

Open this in any browser:
- ✅ Chrome (best support)
- ✅ Firefox
- ✅ Safari
- ✅ Edge
- ✅ Mobile browsers (iPhone Safari, Android Chrome)

---

## 🔑 **Configured Services**

| Service | Status | Purpose |
|---------|--------|---------|
| **Anthropic Claude** | ✅ Active | AI conversation & scoring |
| **ElevenLabs** | ✅ Active | Natural AI voice (most realistic) |
| **Deepgram** | ✅ Active | Speech-to-text (works on all devices) |
| **WebSocket** | ✅ Live | Real-time communication |

**Total cost per session:** ~$0.25-0.30

---

## 🎯 **How to Use**

### **For Testing (You):**
1. Open **http://localhost:5001** in Chrome
2. Enter your name
3. Select "Beginner" difficulty
4. Click "Start Training"
5. Allow microphone access when prompted
6. Listen to the AI customer speak
7. Click microphone button when ready to respond
8. Have a realistic practice conversation!

### **For Your Agents:**
Same steps! They just need the URL (when you deploy to a server).

---

## 🎓 **Training Session Flow**

1. **AI Introduction** (spoken)
   - AI introduces itself as a potential customer
   - Natural, conversational tone

2. **Objection Handling** (3-5 objections)
   - AI presents realistic objections
   - Agent responds using company script
   - Real-time evaluation against objection library

3. **Wrap-up**
   - AI naturally concludes the call
   - Professional ending

4. **Scoring & Feedback**
   - Overall score: 0-10
   - Category breakdown (5 categories)
   - Specific improvement suggestions
   - Full transcript with highlights

---

## 📊 **Scoring System**

| Category | Weight |
|----------|--------|
| Objection Handling | 40% |
| Tone & Confidence | 20% |
| Script Adherence | 15% |
| Active Listening | 15% |
| Professionalism | 10% |

**Grades:**
- 9.0-10.0 = Excellent (ready for live calls)
- 7.0-8.9 = Good (minor improvements)
- 5.0-6.9 = Needs Work (additional training)
- < 5.0 = Not Ready (trainer follow-up)

---

## 🔧 **Next Steps to Customize**

### **1. Add Your Real Objections** (IMPORTANT!)

Edit: [directives/objection_library.md](directives/objection_library.md)

Replace the 5 sample objections with your company's actual scenarios:
- What objections do customers really raise?
- What are the approved responses?
- How should agents handle them?

**Current samples:**
- Price objection
- Timing objection
- Coverage objection
- Trust objection
- Competitor comparison

**Replace these with YOUR objections!**

### **2. Adjust Scoring Weights** (Optional)

Edit: [directives/score_performance.md](directives/score_performance.md)

Change category weights or scoring criteria to match your priorities.

### **3. Modify Training Flow** (Optional)

Edit: [directives/voice_training_session.md](directives/voice_training_session.md)

Adjust:
- Session length (currently 10 minutes)
- Number of objections (currently 3-5)
- Difficulty levels
- AI personality

---

## 🚀 **Deploying to Agents**

**Currently:** Running on localhost (only you can access)

**For team access, you need to:**

### **Option A: Quick Test (ngrok)**
```bash
ngrok http 5001
# Share the https://xxx.ngrok.io URL
```
**Free, temporary, good for testing**

### **Option B: Production Deployment**
Deploy to a cloud server:
- **Railway** (easiest): https://railway.app/
- **Render**: https://render.com/
- **Heroku**: https://heroku.com/
- **AWS/GCP/Azure**: Full control

**Then agents can access from any device!**

---

## 💰 **Cost Tracking**

**Per 10-minute training session:**
- Anthropic Claude: $0.15
- ElevenLabs (voice output): $0.05-0.10
- Deepgram (voice input): $0.05
- **Total: ~$0.25-0.30 per session**

**Monthly estimates:**
- 50 agents × 2 sessions/week = 400 sessions/month = **~$100-120/month**
- 100 agents × 2 sessions/week = 800 sessions/month = **~$200-240/month**

**Compare to:** Hours of manual training time saved!

---

## 🎨 **Features Included**

✅ Realistic AI voice conversations (ElevenLabs)
✅ Universal device support (iPhone, Android, laptop)
✅ Real-time speech-to-text (Deepgram)
✅ Automatic performance scoring (0-10 scale)
✅ 5-category evaluation
✅ Detailed feedback & suggestions
✅ Full conversation transcripts
✅ 3 difficulty levels (beginner/intermediate/advanced)
✅ Beautiful modern UI
✅ WebSocket real-time communication

---

## 📈 **Optional Enhancements**

Want to add later:

### **Google Sheets Logging**
- Track all training sessions
- Analyze agent progress over time
- Identify common weak points

### **Slack Notifications**
- Alert trainers when agents score < 7.0
- Automated follow-up triggers

### **Custom Voices**
- Different AI personalities (male/female, ages)
- Match customer demographics

### **Advanced Features**
- Session recordings for playback
- Progress tracking graphs
- Admin dashboard
- Custom objection scenarios via UI

---

## 🐛 **Troubleshooting**

### Server Not Running?
```bash
cd /Users/edwinlapitan/Documents/Edwin\'s\ AI\ Stuff/Demo
python3 execution/web_voice_server.py
```

### Microphone Not Working?
- Check browser permissions
- Try Chrome (best support)
- Ensure microphone is connected

### Voice Not Playing?
- Check volume settings
- Try different browser
- ElevenLabs API key configured? (it is!)

### Need to Restart?
```bash
pkill -f web_voice_server.py
cd execution
python3 web_voice_server.py
```

---

## 📞 **Support**

**Documentation:**
- [QUICKSTART.md](QUICKSTART.md) - Quick reference
- [SETUP_VOICE_TRAINING.md](SETUP_VOICE_TRAINING.md) - Detailed setup
- [directives/](directives/) - All configuration files

**Server Status:**
- Running on: http://localhost:5001
- Check health: http://localhost:5001/health
- API test: http://localhost:5001/api/test

---

## 🎉 **You're Ready!**

1. ✅ **Test it yourself:** http://localhost:5001
2. ✅ **Customize objections:** Edit directives/objection_library.md
3. ✅ **Train one agent:** Get their feedback
4. ✅ **Iterate:** Adjust scoring, objections, flow
5. ✅ **Deploy:** Make it accessible to your team

**Current Status:** LIVE and FUNCTIONAL! 🚀

---

**Built with:**
- Claude Opus 4.6 (AI orchestration)
- ElevenLabs (realistic voice)
- Deepgram (speech recognition)
- Flask + Socket.IO (real-time web)
- 3-Layer AI Architecture

**Happy Training!** 🎙️📈
