# latency_lab

Autoresearch-style optimization loop for the trainee→AI response latency in the objection-handling roleplay tool.

Modeled on [karpathy/autoresearch](https://github.com/karpathy/autoresearch) but applied to a voice-pipeline latency problem instead of LLM training.

## What it does

An autonomous agent runs every hour via GitHub Actions:

1. Reads `experiments.jsonl` to see what's been tried.
2. Picks one hypothesis to test.
3. Edits `config.json` (the only "code" file the agent touches).
4. Runs `runner.py` against 20 fixed text fixtures.
5. Records `total_ms` (p50/p95) and `quality_score`.
6. If `total_ms` p95 dropped AND `quality_score` ≥ 7.5 → commits to `latency-lab-results` branch as a winner. Else reverts and logs the failure.

## The metric

**`total_ms`** = `claude_ttft_ms` + `tts_ttfb_ms`.

This is the user-perceived gap between trainee finishing speaking and AI starting to speak — minus Deepgram STT time (added back in v2).

Quality guard: Opus grades each response 1-10 against the existing scoring rubric. We never ship a faster-but-dumber config.

## The levers

See `config.json`. The agent edits this file and only this file.

## Files

```
config.json          — knobs the agent tunes (model, tts provider, prompt version, etc.)
program.md           — instructions to the agent
runner.py            — the harness (replaces autoresearch's train.py)
grader.py            — Opus-based quality scoring
fixtures.json        — 20 representative trainee utterances + context
experiments.jsonl    — append-only log of every run
requirements.txt     — Python deps
```

## Running locally

```bash
cd latency_lab
pip install -r requirements.txt
python runner.py        # runs current config.json against all fixtures
```

Append a row to `experiments.jsonl`. No commits, no agent decisions — just measurement.

## Running the agent locally

```bash
claude --dangerously-skip-permissions "follow latency_lab/program.md"
```

## Cloud (GitHub Actions)

`.github/workflows/latency-lab.yml` runs hourly. Secrets required:

- `ANTHROPIC_API_KEY`
- `ELEVENLABS_API_KEY`
- `GOOGLE_TTS_CREDENTIALS_JSON` (optional, for Google TTS branch)

Winners are committed to the `latency-lab-results` branch. `main` is never touched.
