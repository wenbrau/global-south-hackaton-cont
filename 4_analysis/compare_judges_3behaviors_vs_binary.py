"""Judge-vs-judge — 3-CLASS baseline vs BINARY (refuse-only) regrade. **Step 1 of the tests.**

The baseline is the production 3-class judge (`data/3_judged/<dataset>.json`), collapsed to
refuse/not; the regrade is a `run_judge.py` refuse-only run (`refuse: yes/no`). This answers the
first test question: does asking refuse DIRECTLY (binary-collapse prompt) reproduce the refusal
labels you get by deriving them from the 3-class judge post-hoc?

Reports binary refuse/not κ + headline refusal-metric drift. 3-class κ and harm-flag κ are
**n/a** (the regrade has no partial bucket and no harm field).

Run (from anywhere):
    python 4_analysis/compare_judges_3behaviors_vs_binary.py grade_<dataset>_by_<grader>_<ts>.json
    python 4_analysis/compare_judges_3behaviors_vs_binary.py <regrade.json> --baseline data/3_judged/<ds>.json
"""
from __future__ import annotations

import argparse
import os

import _compare_common as cc


def main():
    ap = argparse.ArgumentParser(
        description="Compare a binary refuse-only regrade against the 3-class baseline (collapsed).")
    ap.add_argument("regrade", help="Binary regrade file (path, or bare name in data_regrade/3_judged/).")
    ap.add_argument("--baseline", default=None,
                    help="3-class judged file. Default: data/3_judged/<dataset>.json from the regrade name.")
    ap.add_argument("--out", default=None, help="JSON summary path. Default: next to the regrade file.")
    ap.add_argument("--examples", type=int, default=8, help="How many refuse disagreements to print.")
    args = ap.parse_args()

    regrade_path = cc.resolve_regrade(args.regrade)
    stem = os.path.splitext(os.path.basename(regrade_path))[0]
    dataset, grader = cc.parse_name(regrade_path)

    if args.baseline:
        base_path = args.baseline
    elif dataset:
        base_path = cc._J("data", "3_judged", f"{dataset}.json")
    else:
        raise SystemExit("Could not infer the dataset from the regrade filename; pass --baseline.")
    if not os.path.exists(base_path):
        raise SystemExit(f"baseline not found: {base_path}")

    # Up front: (a) $ cost of the binary judge run, (b) dataset composition
    # (models, languages, modes, domains, contexts, scales) — both from the regrade file.
    cc.print_run_preamble(regrade_path, cc._load(regrade_path))

    out_path = args.out or cc._J("data_regrade", f"compare_{stem}_vs_3class.json")
    cc.run_compare(base_path, regrade_path, base_kind="3class", regrade_kind="binary",
                   dataset=dataset, grader=grader, out_path=out_path, examples=args.examples)


if __name__ == "__main__":
    main()
