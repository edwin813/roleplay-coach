"""Format the latest experiments.jsonl row as a plain-English Telegram HTML message.

Reads env vars: JOB_STATUS, RUN_URL, DASHBOARD_URL.
Prints the message to stdout. Always exits 0.
"""
import json, os, html, pathlib, sys

status = os.environ.get("JOB_STATUS", "?")
run_url = os.environ.get("RUN_URL", "")
dash_url = os.environ.get("DASHBOARD_URL", "")

p = pathlib.Path("latency_lab/experiments.jsonl")
if not p.exists():
    print(f'⚠️ Run failed: no results file. <a href="{run_url}">details</a>')
    sys.exit(0)

rows = []
for line in p.read_text().splitlines():
    line = line.strip()
    if not line:
        continue
    try:
        rows.append(json.loads(line))
    except Exception:
        continue

if not rows:
    print(f'⚠️ Run failed: no experiment recorded. <a href="{run_url}">details</a>')
    sys.exit(0)

latest = rows[-1]
prior = rows[-2] if len(rows) >= 2 else None

decision = latest.get("decision", "PENDING")
res = latest.get("results") or {}
total = res.get("total_ms") or {}
cfg = latest.get("config") or {}

p95_now = total.get("p95")
p50_now = total.get("p50")
q_now = res.get("quality_score")

p95_prev = p50_prev = q_prev = None
prev_cfg = {}
if prior:
    prev_res = prior.get("results") or {}
    prev_total = prev_res.get("total_ms") or {}
    p95_prev = prev_total.get("p95")
    p50_prev = prev_total.get("p50")
    q_prev = prev_res.get("quality_score")
    prev_cfg = prior.get("config") or {}


def sec(ms):
    if ms is None:
        return "—"
    return f"{ms/1000:.1f}s"


def diffs(now, prev):
    """Return list of human-readable changes between two configs."""
    if not prev:
        return []
    out = []
    pretty = {
        "claude_model": "model",
        "claude_max_tokens": "max reply length",
        "claude_streaming": "streaming",
        "prompt_caching": "prompt caching",
        "system_prompt_version": "prompt version",
        "tts_provider": "voice provider",
        "tts_model": "voice model",
        "tts_voice_id": "voice",
    }
    for key, label in pretty.items():
        a = prev.get(key)
        b = now.get(key)
        if a != b:
            if isinstance(b, bool):
                b = "on" if b else "off"
            out.append(f"{label}=<code>{html.escape(str(b))}</code>")
    return out


def err_msg():
    notes = (latest.get("notes") or "").strip()
    errors = latest.get("errors") or []
    if notes:
        msg = notes[:300]
    elif errors:
        msg = errors[0][:300]
    else:
        msg = "see run log"
    return msg


lines = []

if decision == "WIN":
    lines.append("🎉 <b>Faster!</b>")
    changes = diffs(cfg, prev_cfg)
    if changes:
        lines.append("Change: " + ", ".join(changes))
    if p95_now is not None and p95_prev is not None:
        lines.append(f"Reply time: ~{sec(p50_now)} typical, ~{sec(p95_now)} worst case "
                     f"(was ~{sec(p50_prev)} / ~{sec(p95_prev)})")
    elif p95_now is not None:
        lines.append(f"Reply time: ~{sec(p50_now)} typical, ~{sec(p95_now)} worst case")
    if q_now is not None:
        if q_prev is not None:
            lines.append(f"AI sounded natural: <b>{q_now}/10</b> (was {q_prev})")
        else:
            lines.append(f"AI sounded natural: <b>{q_now}/10</b>")

elif decision == "LOSS":
    lines.append("⏸️ <b>No improvement</b> — reverted to previous config")
    changes = diffs(cfg, prev_cfg)
    if changes:
        lines.append("Tried: " + ", ".join(changes))
    if p95_now is not None and p95_prev is not None:
        lines.append(f"Reply time: ~{sec(p50_now)} typical, ~{sec(p95_now)} worst case "
                     f"(was ~{sec(p50_prev)} / ~{sec(p95_prev)})")
    if q_now is not None and q_prev is not None:
        lines.append(f"AI sounded natural: {q_now}/10 (was {q_prev})")

elif decision == "ERROR":
    lines.append("⚠️ <b>Run failed</b>")
    lines.append(html.escape(err_msg()))

else:  # PENDING / unknown
    lines.append("🔬 <b>Run finished</b> (no decision recorded)")
    if p95_now is not None:
        lines.append(f"Reply time: ~{sec(p50_now)} typical, ~{sec(p95_now)} worst case")
    if q_now is not None:
        lines.append(f"AI sounded natural: {q_now}/10")

lines.append(f'📊 <a href="{dash_url}">dashboard</a>')
print("\n".join(lines))
