"""One OpenAI-compatible client. Ollama by default; any free tier by env var.

PRECEDENT_BASE_URL  default http://localhost:11434/v1
PRECEDENT_MODEL     default qwen2.5-coder:7b
PRECEDENT_API_KEY   optional (Groq / Cerebras / OpenRouter / Gemini-compat)
"""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.request

BASE = os.environ.get("PRECEDENT_BASE_URL", "http://localhost:11434/v1").rstrip("/")
MODEL = os.environ.get("PRECEDENT_MODEL", "qwen2.5-coder:7b")
KEY = os.environ.get("PRECEDENT_API_KEY", "")


class Unavailable(RuntimeError):
    pass


def _text(content) -> str:
    """Every provider disagrees about what `content` is.

    OpenAI sends a string. Cloudflare sends a parsed dict when the model emits
    JSON. Others send a list of parts. Callers want text, so give them text
    rather than letting a dict reach a regex three frames later.
    """
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "".join(
            part.get("text", "") if isinstance(part, dict) else str(part)
            for part in content)
    if content is None:
        return ""
    return json.dumps(content)


def chat(prompt: str, system: str = "", timeout: float = 30.0, temperature: float = 0.0) -> str:
    msgs = ([{"role": "system", "content": system}] if system else []) + \
           [{"role": "user", "content": prompt}]
    body = json.dumps({"model": MODEL, "messages": msgs, "temperature": temperature}).encode()
    req = urllib.request.Request(f"{BASE}/chat/completions", data=body,
                                 headers={"Content-Type": "application/json",
                                          **({"Authorization": f"Bearer {KEY}"} if KEY else {})})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return _text(json.loads(r.read())["choices"][0]["message"]["content"])
    except (urllib.error.URLError, OSError, KeyError, json.JSONDecodeError) as e:
        raise Unavailable(str(e)) from e


def available() -> bool:
    try:
        chat("ping", timeout=4.0)
        return True
    except Unavailable:
        return False
