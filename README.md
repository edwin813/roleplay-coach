# 3-Layer AI Architecture

This workspace implements a 3-layer architecture that separates concerns between what to do (directives), decision-making (AI orchestration), and execution (deterministic scripts).

## Directory Structure

```
.
├── directives/          # Layer 1: SOPs in Markdown (what to do)
├── execution/           # Layer 3: Python scripts (doing the work)
├── .tmp/               # Temporary/intermediate files (auto-generated, not committed)
├── CLAUDE.md           # Agent instructions (mirrored as AGENTS.md, GEMINI.md)
├── .env                # Environment variables and API keys
└── credentials.json    # Google OAuth credentials
```

## Setup

1. **Install Python dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Configure environment variables:**
   ```bash
   cp .env.template .env
   # Edit .env and add your API keys
   ```

3. **Set up Google OAuth (if using Google Sheets/Slides):**
   - Go to Google Cloud Console
   - Create a project and enable Google Sheets/Slides API
   - Download credentials.json to this directory
   - First run will generate token.json

4. **Set up Modal (if using webhooks):**
   ```bash
   modal setup
   modal deploy execution/modal_webhook.py
   ```

## Usage

The AI agent (Layer 2) reads directives, calls execution scripts, and handles decision-making. You interact with the agent naturally:

- "Follow the scrape_website directive for example.com"
- "Add a webhook that sends daily reports"
- "Update the contact enrichment directive"

## Key Principles

- **Directives** define goals, inputs, tools, outputs
- **AI** handles routing, errors, clarifications, learning
- **Scripts** are deterministic, tested, reliable
- Local files are temporary - deliverables live in cloud (Sheets, Slides, etc.)
- System self-anneals: errors → fixes → updates → stronger

See [CLAUDE.md](CLAUDE.md) for complete instructions.
