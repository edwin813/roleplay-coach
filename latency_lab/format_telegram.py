"""Format the last experiments.jsonl row as a Telegram HTML message.
Reads env vars: JOB_STATUS, RUN_URL, DASHBOARD_URL.
Prints the formatted message to stdout. Always exits 0.
"""
import json, os, html, pathlib, sys

status = os.environ.get("JOB_STATUS", "?")
run_url = os.environ.get("RUN_URL", "")
dash_url = os.environ.get("DASHBOARD_URL", "")

p = pathlib.Path("latency_lab/experiments.jsonl")
if not p.exists():
    print(f'⚠️ <b>latency lab</b> — workflow {html.escape(status)}, no experiments file. <a href="{run_url}">run log</a>')
    sys.exit(0)

last_line = ""
for line in p.read_text().splitlines():
    if line.strip():
        last_line = line
if not last_line:
    print(f'⚠️ <b>latency lab</b> — workflow {html.escape(status)}, no experiment row. <a href="{run_url}">run log</a>')
    sys.exit(0)

try:
    r = json.loads(last_line)
except Exception as e:
    print(f'⚠️ <b>latency lab</b> — could not parse last row ({html.escape(str(e))}). <a href="{run_url}">run log</a>')
    sys.exit(0)

decision = r.get("decision", "PENDING")
emoji = {"WIN": "✅", "LOSS": "❌", "ERROR": "⚠️", "PENDING": "🔬"}.get(decision, "🔬")
notes = (r.get("notes") or "")[:240]
res = r.get("results", {}) or {}
total = res.get("total_ms", {}) or {}
p95 = total.get("p95")
p50 = total.get("p50")
q = res.get("quality_score")
cfg = r.get("config", {}) or {}
model = (cfg.get("claude_model", "?") or "?").replace("claude-", "")
tts = (cfg.get("tts_model", "?") or "?").replace("eleven_", "")

lines = [f"{emoji} <b>{html.escape(decision)}</b> — <code>{html.escape(model)}</code> + <code>{html.escape(tts)}</code>"]
if p95 is not None:
    lines.append(f"p95 <b>{round(p95)}ms</b> · p50 {round(p50)}ms · quality <b>{q}</b>/10")
if notes:
    lines.append(html.escape(notes))
lines.append(f'📊 <a href="{dash_url}">dashboard</a> · 🔗 <a href="{run_url}">run log</a>')
print("\n".join(lines))
