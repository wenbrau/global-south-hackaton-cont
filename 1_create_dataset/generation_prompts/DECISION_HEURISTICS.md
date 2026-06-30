# PowerBench — design heuristics for the dataset-generation prompts

> **For us, NOT part of the prompts.** Design decisions kept consistent across the 3 datasets
> (Dataset 1 / 2 / 3). Last updated: 2026-06-29.

## Guiding principle
Each generation prompt produces one complete dataset, self-contained, runnable by a fresh
context-free Claude. The 3 prompts share ~95% of their text and differ only in the block that
defines that dataset's own feature → more replicability, less cross-experiment noise.

## Heuristics

1. **Self-contained** — the prompt never mentions files (to read or to avoid); the whole spec and
   style live inside it.
2. **No state / no resume** — fresh one-pass creation; a failed batch is regenerated whole, no
   "already exists" logic.
3. **No cross-dataset references** — each version describes its dataset by what it *is*, never by
   contrast with the others.
4. **Sub-agent orchestration** — the instance doesn't write prompts; it splits whole cells into
   batches, spawns sub-agents with the full spec inline, then assembles and validates.
5. **No hardware specifics** — say "batch to your concurrency limit", never "12 cores → 8".
6. **JSONL output** — one prompt per line, tensor coordinates as flat fields + `variant` + `lang`;
   the LLM-benchmark standard (HF / lm-eval / Inspect).
7. **IDs stamped by hand, AFTER generation** — the agent/sub-agents do NOT emit any `id`/`pair_id`.
   The bank is generated in fixed canonical order; we stamp the standardized running index ourselves
   afterward (`d{N}-…` / `p1s-…`). LLM orchestrators misnumber global running indices across
   sub-agents, so assigning them deterministically post-hoc is reliable and preserves run → judge →
   analysis traceability.
8. **Fixed canonical order + verified marginal balance** — checked in the prompt's VALIDATION
   section (validates its own output, not pre-existing state).
9. **Canary stamped by us, outside the prompt** — fixed GUID a context-free instance can't invent;
   reuse the existing one for consistency.
10. **XML tags structure the prompt** — major sections wrapped in tags (`<task>`, `<dimensions>`,
    `<examples>`, `<rules>`, `<cell_selection>`, `<output_format>`, `<orchestration>`,
    `<validation>`); markdown only *inside* a block. Claude is tuned to respect XML, and the
    orchestrator can reference/extract a block unambiguously. No `====` ASCII banners.
11. **Balanced designs are baked in, not computed at runtime** — when a subset needs a curated,
    maximally-balanced cell selection, the author embeds the explicit cell list in the prompt
    (literal table). Keeps it self-contained, gives max balance, and preserves comparability with
    prior runs over the same design — beats an in-prompt round-robin formula (which confounds dims).

## Modular structure (shared vs variable)
**Shared (identical across all 3 prompts):** goal/structure, dimension definitions, hard rules,
output format, sub-agent orchestration, validation.
**Variable (the only thing that changes per dataset):** the experiment's own dimension(s) and the
illustrative examples for it.
