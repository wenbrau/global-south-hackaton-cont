"""Shared sys.path bootstrap for every pipeline script.

The pipeline is split across numbered stage folders (1_create_dataset,
2_run_targets, 3_judge, 4_analysis) plus this ``common/`` engine. Modules are
still imported by bare name (``engine``, ``judge``, ``all_prompts_576``, ...),
so any script can make them importable -- regardless of which folder it lives in
or which directory you run it from -- with two lines::

    import os, sys
    _d = os.path.dirname(os.path.abspath(__file__))
    while _d != os.path.dirname(_d) and not os.path.isdir(os.path.join(_d, "common")):
        _d = os.path.dirname(_d)
    sys.path.insert(0, os.path.join(_d, "common")); import _paths  # noqa

Importing this module puts the engine, the prompt banks, the judge and the
Inspect helpers on ``sys.path``.
"""
import os
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

for _p in (
    "common",
    "1_create_dataset",
    "1_create_dataset/prompts",
    "1_create_dataset/nationality",
    "2_run_targets",
    "3_judge",
):
    _ap = os.path.join(_ROOT, *_p.split("/"))
    if _ap not in sys.path:
        sys.path.insert(0, _ap)
