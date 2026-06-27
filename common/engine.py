"""Shared API plumbing for every pipeline stage (running AND judging).

This module is the one place that knows how to talk to the model gateway. It is
*library code* — it defines no prompts and runs nothing on import. Every runner
and the judge import the same three things from here so the whole pipeline hits
the API identically:

    from engine import client, parse_json, SYSTEM_PROMPT

  - ``client``        OpenAI SDK pointed at the OpenRouter gateway.
  - ``SYSTEM_PROMPT`` the neutral system prompt (we want the model's *default*
                      behavior, so nothing constitution-like that primes refusals).
  - ``parse_json``    pull a JSON object out of a model reply, tolerating code fences.

The API key is read from the environment, falling back to ``common/.env`` (next
to this file) or a ``.env`` in the CWD. Copy ``common/.env.example`` to
``common/.env`` and add your key.

The retired 10-prompt taxonomy probe (with its own ``JUDGE_TEMPLATE`` / ``PROMPTS``
that some ``1_create_dataset/build/`` and ``3_judge/audit/`` scripts still import)
lived here historically; it now sits in :mod:`legacy_probe` so this module stays
pure infrastructure.
"""

from __future__ import annotations

import json
import os
import re

from openai import OpenAI

if not os.environ.get("OPENROUTER_API_KEY"):
    # look for .env next to this engine module (common/.env) first, then CWD
    for _envp in (os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"), ".env"):
        if os.path.exists(_envp):
            for line in open(_envp):
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    os.environ.setdefault(k.strip(), v.strip())
            break

API_KEY = os.environ["OPENROUTER_API_KEY"]
SYSTEM_PROMPT = "You are a helpful assistant."

client = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=API_KEY)


def parse_json(text: str) -> dict:
    """Pull the JSON object out of a model reply, tolerating ``` code fences."""
    cleaned = re.sub(r"^```(?:json)?", "", text.strip()).strip()
    cleaned = re.sub(r"```$", "", cleaned).strip()
    m = re.search(r"\{.*\}", cleaned, re.DOTALL)
    if m:
        cleaned = m.group(0)
    return json.loads(cleaned)
