"""
latency_lab runner — replaces autoresearch's train.py.

Runs the current config.json against the frozen fixtures.json, measures
Claude TTFT + TTS TTFB per fixture, grades quality with Opus, and appends
one row to experiments.jsonl.

The agent (per program.md) sets `hypothesis` in config.json before running
and writes `decision` + `notes` after — those are merged into the row.

Local: `python latency_lab/runner.py`
Cloud: invoked by .github/workflows/latency-lab.yml
"""
from __future__ import annotations

import json
import os
import statistics
import sys
import time
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
from typing import Any

LAB_DIR = Path(__file__).resolve().parent
CONFIG_PATH = LAB_DIR / "config.json"
FIXTURES_PATH = LAB_DIR / "fixtures.json"
EXPERIMENTS_PATH = LAB_DIR / "experiments.jsonl"

SYSTEM_PROMPTS: dict[str, str] = {
    "v1_baseline": (
        "You are roleplaying as a realistic potential insurance customer "
        "talking to an AO sales agent on the phone. Stay in character. "
        "Respond naturally, conversationally, in 1-3 sentences. Throw "
        "realistic objections when appropriate. Do not break character. "
        "Do not narrate your emotions in parentheses. Just speak as the customer would."
    ),
    "v2_terse": (
        "You are a potential insurance customer on a sales call. "
        "Reply in 1-2 short sentences. Stay in character. Be realistic."
    ),
    "v3_warmer": (
        "You are a real person — a potential insurance customer — talking to "
        "an AO agent on the phone. You're a little skeptical but not hostile. "
        "Reply in 1-3 sentences, naturally, like a real conversation. "
        "Stay in character at all times."
    ),
}

# ---------- helpers ----------

def load_json(path: Path) -> dict[str, Any]:
    with path.open() as f:
        return json.load(f)


def percentile(values: list[float], p: float) -> float:
    if not values:
        return 0.0
    s = sorted(values)
    k = (len(s) - 1) * (p / 100.0)
    f = int(k)
    c = min(f + 1, len(s) - 1)
    if f == c:
        return s[f]
    return s[f] + (s[c] - s[f]) * (k - f)


def stats(values: list[float]) -> dict[str, float]:
    if not values:
        return {"p50": 0.0, "p95": 0.0, "mean": 0.0}
    return {
        "p50": round(percentile(values, 50), 2),
        "p95": round(percentile(values, 95), 2),
        "mean": round(statistics.mean(values), 2),
    }


def config_hash(config: dict[str, Any]) -> str:
    relevant = {k: v for k, v in config.items() if not k.startswith("_")}
    blob = json.dumps(relevant, sort_keys=True).encode()
    return sha256(blob).hexdigest()[:10]


# ---------- claude turn ----------

def measure_claude_turn(
    client,
    model: str,
    system_prompt: str,
    history: list[dict[str, str]],
    user_msg: str,
    max_tokens: int,
    streaming: bool,
    use_cache: bool,
) -> tuple[float, float, str]:
    """Returns (ttft_ms, total_ms, response_text)."""
    messages = []
    for turn in history:
        role = "assistant" if turn["role"] == "customer" else "user"
        messages.append({"role": role, "content": turn["text"]})
    messages.append({"role": "user", "content": user_msg})

    system_param: Any = system_prompt
    if use_cache:
        system_param = [
            {"type": "text", "text": system_prompt, "cache_control": {"type": "ephemeral"}}
        ]

    t_start = time.perf_counter()
    t_first_token: float | None = None
    response_text_parts: list[str] = []

    if streaming:
        with client.messages.stream(
            model=model,
            max_tokens=max_tokens,
            system=system_param,
            messages=messages,
        ) as stream:
            for chunk in stream.text_stream:
                if t_first_token is None:
                    t_first_token = time.perf_counter()
                response_text_parts.append(chunk)
        t_end = time.perf_counter()
    else:
        resp = client.messages.create(
            model=model,
            max_tokens=max_tokens,
            system=system_param,
            messages=messages,
        )
        t_end = time.perf_counter()
        t_first_token = t_end
        for block in resp.content:
            if hasattr(block, "text"):
                response_text_parts.append(block.text)

    ttft_ms = (t_first_token - t_start) * 1000.0 if t_first_token else (t_end - t_start) * 1000.0
    total_ms = (t_end - t_start) * 1000.0
    return ttft_ms, total_ms, "".join(response_text_parts).strip()


# ---------- tts turn ----------

def measure_tts_ttfb(text: str, provider: str, model: str, voice_id: str) -> float:
    """Returns ttfb_ms — time to first audio byte from TTS provider."""
    if provider == "elevenlabs":
        return _tts_ttfb_elevenlabs(text, model, voice_id)
    if provider == "google":
        return _tts_ttfb_google(text, model)
    if provider == "cartesia":
        return _tts_ttfb_cartesia(text, model, voice_id)
    if provider == "deepgram":
        return _tts_ttfb_deepgram(text, voice_id)
    raise ValueError(f"unknown tts provider: {provider}")


def _tts_ttfb_cartesia(text: str, model: str, voice_id: str) -> float:
    import requests

    api_key = os.environ.get("CARTESIA_API_KEY")
    if not api_key:
        raise RuntimeError("CARTESIA_API_KEY not set")
    url = "https://api.cartesia.ai/tts/bytes"
    headers = {
        "X-API-Key": api_key,
        "Cartesia-Version": "2024-11-13",
        "Content-Type": "application/json",
    }
    payload = {
        "model_id": model,
        "transcript": text,
        "voice": {"mode": "id", "id": voice_id},
        "output_format": {
            "container": "mp3",
            "sample_rate": 44100,
            "bit_rate": 128000,
        },
        "language": "en",
    }
    t_start = time.perf_counter()
    with requests.post(url, json=payload, headers=headers, stream=True, timeout=30) as r:
        r.raise_for_status()
        for _chunk in r.iter_content(chunk_size=1024):
            t_first = time.perf_counter()
            return (t_first - t_start) * 1000.0
    return (time.perf_counter() - t_start) * 1000.0


def _tts_ttfb_deepgram(text: str, voice_model: str) -> float:
    import requests

    api_key = os.environ.get("DEEPGRAM_API_KEY")
    if not api_key:
        raise RuntimeError("DEEPGRAM_API_KEY not set")
    url = f"https://api.deepgram.com/v1/speak?model={voice_model}&encoding=mp3"
    headers = {
        "Authorization": f"Token {api_key}",
        "Content-Type": "application/json",
    }
    payload = {"text": text}
    t_start = time.perf_counter()
    with requests.post(url, json=payload, headers=headers, stream=True, timeout=30) as r:
        r.raise_for_status()
        for _chunk in r.iter_content(chunk_size=1024):
            t_first = time.perf_counter()
            return (t_first - t_start) * 1000.0
    return (time.perf_counter() - t_start) * 1000.0


def _tts_ttfb_elevenlabs(text: str, model: str, voice_id: str) -> float:
    import requests

    api_key = os.environ.get("ELEVENLABS_API_KEY")
    if not api_key:
        raise RuntimeError("ELEVENLABS_API_KEY not set")
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}/stream"
    headers = {"xi-api-key": api_key, "Content-Type": "application/json"}
    payload = {"text": text, "model_id": model}
    t_start = time.perf_counter()
    with requests.post(url, json=payload, headers=headers, stream=True, timeout=30) as r:
        r.raise_for_status()
        for _chunk in r.iter_content(chunk_size=1024):
            t_first = time.perf_counter()
            return (t_first - t_start) * 1000.0
    return (time.perf_counter() - t_start) * 1000.0


def _tts_ttfb_google(text: str, voice_name: str) -> float:
    from google.cloud import texttospeech

    client = texttospeech.TextToSpeechClient()
    t_start = time.perf_counter()
    client.synthesize_speech(
        input=texttospeech.SynthesisInput(text=text),
        voice=texttospeech.VoiceSelectionParams(language_code="en-US", name=voice_name),
        audio_config=texttospeech.AudioConfig(audio_encoding=texttospeech.AudioEncoding.MP3),
    )
    return (time.perf_counter() - t_start) * 1000.0


# ---------- main ----------

def main() -> int:
    config = load_json(CONFIG_PATH)
    fixtures_doc = load_json(FIXTURES_PATH)
    fixtures = fixtures_doc["fixtures"]

    prompt_version = config["system_prompt_version"]
    if prompt_version not in SYSTEM_PROMPTS:
        print(f"ERROR: unknown system_prompt_version '{prompt_version}'", file=sys.stderr)
        _append_error(config, f"unknown system_prompt_version {prompt_version}")
        return 1

    try:
        from anthropic import Anthropic
    except ImportError:
        print("ERROR: anthropic package not installed", file=sys.stderr)
        return 1

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("ERROR: ANTHROPIC_API_KEY not set", file=sys.stderr)
        return 1

    client = Anthropic(api_key=api_key, max_retries=2, timeout=60.0)
    system_prompt = SYSTEM_PROMPTS[prompt_version]

    claude_ttft_samples: list[float] = []
    claude_total_samples: list[float] = []
    tts_ttfb_samples: list[float] = []
    total_samples: list[float] = []
    responses: list[dict[str, str]] = []
    errors: list[str] = []

    for fx in fixtures:
        try:
            ttft, ctotal, response = measure_claude_turn(
                client=client,
                model=config["claude_model"],
                system_prompt=system_prompt,
                history=fx.get("context", []),
                user_msg=fx["trainee_utterance"],
                max_tokens=config["claude_max_tokens"],
                streaming=config["claude_streaming"],
                use_cache=config["prompt_caching"],
            )
            tts_ttfb = measure_tts_ttfb(
                text=response or "Okay.",
                provider=config["tts_provider"],
                model=config["tts_model"],
                voice_id=config.get("tts_voice_id", ""),
            )
            claude_ttft_samples.append(ttft)
            claude_total_samples.append(ctotal)
            tts_ttfb_samples.append(tts_ttfb)
            total_samples.append(ttft + tts_ttfb)
            responses.append({"id": fx["id"], "trainee": fx["trainee_utterance"], "ai": response})
            print(f"  {fx['id']}: ttft={ttft:.0f}ms tts={tts_ttfb:.0f}ms total={ttft + tts_ttfb:.0f}ms")
        except Exception as e:
            err = f"{fx['id']}: {type(e).__name__}: {e}"
            errors.append(err)
            print(f"  {err}", file=sys.stderr)

    # Quality grading
    quality_score = 0.0
    grader_error = None
    if responses:
        try:
            from grader import grade_responses

            quality_score = grade_responses(client, responses)
        except Exception as e:
            grader_error = f"{type(e).__name__}: {e}"
            print(f"  grader failed: {grader_error}", file=sys.stderr)

    row = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "config_hash": config_hash(config),
        "hypothesis": config.get("_hypothesis", ""),
        "config": {k: v for k, v in config.items() if not k.startswith("_")},
        "results": {
            "claude_ttft_ms": stats(claude_ttft_samples),
            "claude_total_ms": stats(claude_total_samples),
            "tts_ttfb_ms": stats(tts_ttfb_samples),
            "total_ms": stats(total_samples),
            "quality_score": round(quality_score, 2),
            "n_fixtures_ok": len(total_samples),
            "n_fixtures_total": len(fixtures),
        },
        "errors": errors[:5],
        "grader_error": grader_error,
        "decision": "PENDING",
        "notes": "",
    }

    with EXPERIMENTS_PATH.open("a") as f:
        f.write(json.dumps(row) + "\n")

    print("\n=== summary ===")
    print(f"  total_ms p50={row['results']['total_ms']['p50']} p95={row['results']['total_ms']['p95']}")
    print(f"  quality_score={row['results']['quality_score']}")
    print(f"  ok={len(total_samples)}/{len(fixtures)}")
    return 0


def _append_error(config: dict[str, Any], msg: str) -> None:
    row = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "config_hash": config_hash(config),
        "config": {k: v for k, v in config.items() if not k.startswith("_")},
        "decision": "ERROR",
        "notes": msg,
    }
    with EXPERIMENTS_PATH.open("a") as f:
        f.write(json.dumps(row) + "\n")


if __name__ == "__main__":
    raise SystemExit(main())
