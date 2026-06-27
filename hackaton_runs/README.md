# `hackaton_runs/` — the original all-in-one runners ⚠️

> [!WARNING]
> **These scripts run the TARGET *and* the JUDGE together, in one pass.**
> Each `run_*.py` here queries the target model and then immediately calls the
> blind judge inline, writing the verdict onto the same record in
> `data/3_judged/`. So **running one of these spends BOTH the target tokens and
> the judge tokens** — there is no cheap "just regenerate answers" or "just
> re-grade" here. This is the expensive, coupled flow from the hackathon.

These produced the canonical `data/3_judged/*.json` files we already have, and we
do **not** want to re-run them (cost). They're kept as provenance and as resume-
aware entry points if a run ever has to be extended.

**Frozen, self-contained judge.** These runners grade with their OWN pinned copy
of the judge — [`judge.py`](judge.py) + [`judge_prompt.txt`](judge_prompt.txt) in
this folder — *not* the one in `3_judge/`. That keeps this archive reproducible:
`3_judge/` is free to evolve (new models/prompts, the multi-judge work) without
changing what these frozen runners would produce. (The two judges are byte-identical
today; the split is about provenance, not a behavior difference.) Each runner adds
its own folder to the front of `sys.path` so `import judge` picks the local copy.

## What's here

| Script | Targets × design | Output (`data/3_judged/`) |
|---|---|---|
| `run_5models_4langs.py` | 5 models × 4 langs × 576 (main panel) | `5models_4langs.json` |
| `run_single_target_sweep.py` | 1 configurable target × N langs (env `TARGETS`/`LANGS`/`OUT`) | `minimax_8langs.json` (default); also made `gemini_4langs.json`, `*_aiagent.json` |
| `run_2models_dyads_nationality.py` | minimax + gemini × nationality directed dyads | `2models_dyads_nationality.json` |
| `run_nationality.py` | minimax × 1728-cell nationality tensor (legacy) | `experiment_nationality_results.json` |
| `run_nationality_human_gemini.py` | gemini × nationality "human" control | `nationality_human_gemini*.json` |
| `run_nationality_human_minimax.py` | minimax × nationality "human" control | `nationality_human_minimax*.json` |
| `run_probe150_7models.py` | 7 secondary models × 150-combo subset × en/zh | `probe150_7models.json` |

The 150-combo subset design is in
[`../1_create_dataset/subsets/design150_combos.json`](../1_create_dataset/subsets/design150_combos.json).

## The right way going forward (decoupled)

Don't add new all-in-one runners. Instead split the two stages so judging is cheap
to repeat (this is what the multi-judge work needs):

1. **Target only →** write `data/2_responses/<name>.json` (answers, no verdict).
2. **Judge →** [`../3_judge/run_judge.py`](../3_judge/run_judge.py) reads that
   file and writes `data/3_judged/<name>.json`. Re-judging (different model /
   prompt / effort) never re-queries the targets.

The existing `data/2_responses/` snapshots for the runs here were derived
*backwards* from `data/3_judged/` by
[`../2_run_targets/make_responses_snapshot.py`](../2_run_targets/make_responses_snapshot.py)
(a one-time legacy backfill, since these runners judged in place).
