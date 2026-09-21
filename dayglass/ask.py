"""Ask a local OpenAI-compatible server. Localhost only."""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request

DEFAULT_URLS = (
    "http://127.0.0.1:1234/v1",
    "http://127.0.0.1:1235/v1",
)
DEFAULT_MODEL = "qwen3.8-27b-mlx@4bit"
FALLBACK_MODEL = "qwen3-4b-instruct-2507-mlx"


def _chat(base: str, model: str, prompt: str, timeout: int = 35) -> str:
    body = json.dumps(
        {
            "model": model,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You answer from the user's own screen notes. "
                        "Be direct. If the notes do not say it, say so."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.2,
            "max_tokens": 800,
        }
    ).encode()
    req = urllib.request.Request(
        base.rstrip("/") + "/chat/completions",
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        payload = json.loads(resp.read().decode())
    return payload["choices"][0]["message"]["content"].strip()


def complete(prompt: str) -> str:
    model = os.environ.get("DAYGLASS_MODEL", DEFAULT_MODEL)
    urls = [os.environ.get("DAYGLASS_BASE_URL")] if os.environ.get("DAYGLASS_BASE_URL") else list(DEFAULT_URLS)
    errors: list[str] = []
    for base in urls:
        if not base or not base.startswith("http://127.0.0.1"):
            errors.append("refusing non-localhost base")
            continue
        for candidate in (model, FALLBACK_MODEL):
            try:
                return _chat(base, candidate, prompt, timeout=75)
            except (urllib.error.URLError, TimeoutError, KeyError, json.JSONDecodeError) as exc:
                errors.append(f"{base} {candidate}: {exc}")
    raise RuntimeError("local model unreachable: " + "; ".join(errors[-4:]))
