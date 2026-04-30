# latency_lab — agent program

You are running an autonomous optimization loop for the trainee→AI response latency in the AO objection-handling roleplay tool. This file is your only source of truth for what to do. Read it fully before acting.

## Goal

Minimize `total_ms` p95 across 20 fixed text fixtures, while keeping `quality_score` ≥ 7.5/10.

`total_ms` = `claude_ttft_ms` + `tts_ttfb_ms` (the gap a trainee perceives between finishing speaking and hearing the AI reply).

## What you can change

You may edit **only one file**: `latency_lab/config.json`. That's the entire surface area. Do not edit `runner.py`, `grader.py`, `fixtures.json`, or anything outside `latency_lab/`.

The legal levers are documented inline in `config.json`. Do not invent fields the runner doesn't read.

## What you do, in order

You run **3 experiments per invocation**, sequentially, in a loop. Each experiment tests one distinct hypothesis. The 3 hypotheses must be non-overlapping (different levers, or clearly different values on the same lever).

1. **Read** `latency_lab/experiments.jsonl`. Every prior run is logged there with the full config and results. Skim the last 20 entries minimum.
2. **Read** `latency_lab/config.json` — the current best-known config. Remember this as the "baseline" you'll revert to between LOSS experiments.
3. **Form 3 distinct hypotheses** up front. Each must change exactly one lever (or one combo if prior data justifies it). Hypotheses must not overlap with each other or with disproven configs in `experiments.jsonl`. Examples of a valid trio:
   - H1: "Switching `claude_model` from sonnet-4-6 to haiku-4-5 will cut TTFT ~40%."
   - H2: "Reducing `claude_max_tokens` from 150 to 80 will cut total Claude time."
   - H3: "Switching `tts_model` from `eleven_turbo_v2_5` to `eleven_flash_v2_5` will cut TTS TTFB."
4. **For each hypothesis (1, 2, 3), in turn:**
   a. **Edit** `config.json` to reflect that hypothesis (starting from the current winning config).
   b. **Run** `python latency_lab/runner.py`. It executes the fixtures, grades quality, and appends a row to `experiments.jsonl`.
   c. **Decide.** If new row's `total_ms_p95` < the most recent WIN's `total_ms_p95` AND `quality_score` ≥ 7.5 → **WIN**: leave `config.json` as-is (it becomes the new winning config for the remaining experiments in this invocation). Edit the just-appended row of `experiments.jsonl` so its `decision` field is `"WIN"` and `notes` is a one-sentence summary like `"sonnet-4-6 → haiku-4-5: p95 1931→1275, q 8.5→9.0"`.
   d. Else → **LOSS**: revert `config.json` to the most recent WIN config (or the baseline you noted in step 2 if no WINs yet this invocation). Edit the just-appended row of `experiments.jsonl` so its `decision` field is `"LOSS"` and `notes` explains why.
5. **DO NOT run any git commands. The workflow handles all commits and pushes.** You only edit files.
6. **Stop after the 3rd experiment.** Print one final line: `lab: <N>/3 WINs — <one-sentence summary of the best result>`. GitHub Actions runs you again in 30 minutes.

## Hard rules

- **Never run `git` commands.** The workflow handles commits and pushes. You only edit files.
- 3 hypotheses per invocation, run sequentially. Each is one lever change (or one combo with cited justification). No bundled changes within a single experiment.
- Never edit `runner.py` or `grader.py`. If they're broken, log the failure to `experiments.jsonl` with `error: ...` and stop.
- Never modify `fixtures.json` — comparability across runs depends on it being frozen.
- If `quality_score` drops below 7.5, that's a hard fail regardless of latency. Revert.
- If you can't decide on a hypothesis (ran out of obvious ideas), pick a less-tested area of the config space rather than repeating winners.

## Hypothesis priority order (rough)

When in doubt, try in this order — these are expected to have the largest impact first:

1. `tts_provider` — biggest unexplored lever. Cartesia Sonic (~40ms TTFB) and Deepgram Aura-2 (~90ms) are both expected to beat ElevenLabs Flash (~75-150ms). Try `cartesia` with `sonic-2` first — likely the single largest TTFB win available. NOTE: ElevenLabs free tier is exhausted as of 2026-04-29 (quota_exceeded), so ElevenLabs experiments will return HTTP 401 until quota resets monthly — log as ERROR and skip. Do NOT pick `google` — `GOOGLE_APPLICATION_CREDENTIALS_JSON` secret is not configured in CI, all 20 fixtures will DefaultCredentialsError.
2. `claude_model` — Haiku 4.5 is dramatically faster TTFT than Sonnet 4.6 or Opus 4.7.
3. `tts_model` — within ElevenLabs, `eleven_flash_v2_5` is ~75ms TTFB vs ~250ms for `eleven_turbo_v2_5`. Within Cartesia, `sonic-turbo` is fastest but caps at 500 chars (fine for 1-3 sentence replies); `sonic-2` is the safe default.
4. `prompt_caching` — large wins on cached system prompts.
5. `claude_max_tokens` — shorter responses = lower `claude_total_ms`, but watch quality.
6. `system_prompt_version` — trim the persona prompt; every token costs latency.

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

After all 3 experiments, print one line: `lab: <N>/3 WINs — <one-sentence summary of best result>`. That's the only output that matters.
