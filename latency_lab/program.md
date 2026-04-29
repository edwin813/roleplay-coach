# latency_lab — agent program

You are running an autonomous optimization loop for the trainee→AI response latency in the AO objection-handling roleplay tool. This file is your only source of truth for what to do. Read it fully before acting.

## Goal

Minimize `total_ms` p95 across 20 fixed text fixtures, while keeping `quality_score` ≥ 7.5/10.

`total_ms` = `claude_ttft_ms` + `tts_ttfb_ms` (the gap a trainee perceives between finishing speaking and hearing the AI reply).

## What you can change

You may edit **only one file**: `latency_lab/config.json`. That's the entire surface area. Do not edit `runner.py`, `grader.py`, `fixtures.json`, or anything outside `latency_lab/`.

The legal levers are documented inline in `config.json`. Do not invent fields the runner doesn't read.

## What you do, in order

1. **Read** `latency_lab/experiments.jsonl`. Every prior run is logged there with the full config and results. Skim the last 20 entries minimum.
2. **Read** `latency_lab/config.json` — the current best-known config.
3. **Form one hypothesis.** Pick a single change you believe will lower `total_ms` p95 without dropping `quality_score` below 7.5. Examples:
   - "Switching `claude_model` from sonnet-4-6 to haiku-4-5 will cut TTFT ~40%."
   - "Reducing `claude_max_tokens` from 150 to 80 will cut total Claude time."
   - "Switching `tts_model` from `eleven_turbo_v2_5` to `eleven_flash_v2_5` will cut TTS TTFB."
   - "Enabling `prompt_caching` will cut TTFT on cached prefixes."
   Avoid hypotheses already disproven in `experiments.jsonl` — don't re-run the same config.
4. **Edit** `config.json` to reflect the new hypothesis. Change ONE lever per run unless prior data justifies a combo.
5. **Run** `python latency_lab/runner.py`. It will execute the fixtures, grade quality, and append a row to `experiments.jsonl`.
6. **Decide:**
   - If new row's `total_ms_p95` < the last winning config's `total_ms_p95` AND `quality_score` ≥ 7.5 → **keep**: commit `config.json` + `experiments.jsonl` to the `latency-lab-results` branch with message `lab: WIN <hypothesis> — <old_p95>ms → <new_p95>ms (q=<score>)`.
   - Else → **revert** `config.json` to the last winning config (find it in `experiments.jsonl`) and commit only `experiments.jsonl` with message `lab: LOSS <hypothesis> — <result>`.
7. **Stop after one experiment.** GitHub Actions runs you again next hour.

## Hard rules

- One hypothesis per run. No bundled changes unless you have a strong reason and you cite it in the commit message.
- Never push to `main`. Only `latency-lab-results`.
- Never edit `runner.py` or `grader.py`. If they're broken, log the failure to `experiments.jsonl` with `error: ...` and stop.
- Never modify `fixtures.json` — comparability across runs depends on it being frozen.
- If `quality_score` drops below 7.5, that's a hard fail regardless of latency. Revert.
- If you can't decide on a hypothesis (ran out of obvious ideas), pick a less-tested area of the config space rather than repeating winners.

## Hypothesis priority order (rough)

When in doubt, try in this order — these are expected to have the largest impact first:

1. `claude_model` — Haiku 4.5 is dramatically faster TTFT than Sonnet 4.6 or Opus 4.7.
2. `tts_model` — `eleven_flash_v2_5` is ~75ms TTFB vs ~250ms for `eleven_turbo_v2_5`.
3. `prompt_caching` — large wins on cached system prompts.
4. `claude_max_tokens` — shorter responses = lower `claude_total_ms`, but watch quality.
5. `system_prompt_version` — trim the persona prompt; every token costs latency.
6. `tts_provider` — google vs elevenlabs.

## Logging discipline

Every row you append to `experiments.jsonl` MUST include:

```json
{
  "timestamp": "ISO-8601",
  "git_sha": "<short hash of config.json content>",
  "hypothesis": "one-sentence prediction",
  "config": { ... full config.json ... },
  "results": {
    "claude_ttft_ms": {"p50": ..., "p95": ..., "mean": ...},
    "tts_ttfb_ms": {"p50": ..., "p95": ..., "mean": ...},
    "total_ms": {"p50": ..., "p95": ..., "mean": ...},
    "quality_score": <float>,
    "n_fixtures": 20
  },
  "decision": "WIN | LOSS | ERROR",
  "notes": "free-form, max 200 chars"
}
```

The runner writes most of this for you. Your job is to set `hypothesis` before running and `decision` + `notes` after.

## When you finish

Print one line: `lab: <decision> — <one-sentence summary>`. That's the only output that matters.
