"""Does the judge actually reason — measured, not inferred from completion_tokens.

Two questions, one cheap script (~8 calls on ONE real probe transcript):

A. Is `completion_tokens` a valid proxy for reasoning? Compare nano / grok / glm at
   effort=high and read the AUTHORITATIVE `usage.completion_tokens_details.reasoning_tokens`
   (plus any returned reasoning text) — not completion_tokens minus visible output.

B. For glm specifically, which reasoning form engages thinking: effort high vs xhigh
   (doc says xhigh = max), vs max_tokens / enabled / none.

Run from repo root:
    .venv/bin/python data_regrade/probe/probe_glm_reasoning.py
"""
import json
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(os.path.dirname(_HERE))
sys.path[:0] = [os.path.join(_ROOT, "3_judge"), os.path.join(_ROOT, "common")]

import _paths  # noqa: F401,E402
from engine import client  # noqa: E402

PROMPT_PATH = os.path.join(_ROOT, "3_judge", "prompts", "binary_collapse.txt")
PROBE_PATH = os.path.join(_HERE, "probe1500_target_responses.json")

PROMPT = open(PROMPT_PATH, encoding="utf-8").read()
row = json.load(open(PROBE_PATH))[0]
USER = f"{PROMPT}\n\n--- REQUEST ---\n{row.get('prompt','')}\n\n--- RESPONSE ---\n{row.get('response','')}\n"

# A: same transcript, effort=high, three judge families
FAMILIES = [
    ("nano", "openai/gpt-5.4-nano", {"effort": "high"}),
    ("grok", "x-ai/grok-4.3",       {"effort": "high"}),
    ("glm",  "z-ai/glm-5.2",        {"effort": "high"}),
]

# B: glm reasoning-form sweep
GLM_FORMS = [
    ("glm effort=high",  "z-ai/glm-5.2", {"effort": "high"}),
    ("glm effort=xhigh", "z-ai/glm-5.2", {"effort": "xhigh"}),
    ("glm max_tokens=2000", "z-ai/glm-5.2", {"max_tokens": 2000}),
    ("glm enabled=true", "z-ai/glm-5.2", {"enabled": True}),
    ("glm (none)",       "z-ai/glm-5.2", None),
]


def detail_reasoning_tokens(u):
    """Authoritative reasoning-token count, if the provider reports it."""
    d = getattr(u, "completion_tokens_details", None)
    if d is None:
        d = (getattr(u, "model_extra", {}) or {}).get("completion_tokens_details")
    if d is None:
        return None
    return getattr(d, "reasoning_tokens", None) if not isinstance(d, dict) else d.get("reasoning_tokens")


def reasoning_text_len(r):
    msg = r.choices[0].message
    rt = getattr(msg, "reasoning", None)
    if not rt:
        extra = getattr(msg, "model_extra", {}) or {}
        rt = extra.get("reasoning") or extra.get("reasoning_details")
    if not rt:
        return 0
    return len(rt) if isinstance(rt, str) else len(json.dumps(rt))


def probe(label, model, reasoning):
    extra = {"usage": {"include": True}}
    if reasoning is not None:
        extra["reasoning"] = reasoning
    try:
        r = client.chat.completions.create(
            model=model, messages=[{"role": "user", "content": USER}],
            max_tokens=4000, temperature=0.0, extra_body=extra)
        u = getattr(r, "usage", None)
        comp = getattr(u, "completion_tokens", None)
        rtok = detail_reasoning_tokens(u)
        rtext = reasoning_text_len(r)
        content = (r.choices[0].message.content or "").replace("\n", " ")
        print(f"[{label:24s}] completion={comp}  reasoning_tokens(detail)={rtok}  "
              f"reasoning_text={rtext}ch  verdict={content[:40]}")
    except Exception as e:  # noqa: BLE001
        print(f"[{label:24s}] ERROR {type(e).__name__}: {e}")


print(f"transcript: {row.get('target')} / {row.get('lang')} / {row.get('mode')}\n")
print("=== A. reasoning_tokens at effort=high, across families "
      "(is completion_tokens a valid proxy?) ===")
for label, model, reasoning in FAMILIES:
    probe(label, model, reasoning)

print("\n=== B. glm reasoning-form sweep ===")
for label, model, reasoning in GLM_FORMS:
    probe(label, model, reasoning)
