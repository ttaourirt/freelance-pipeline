"""Couche LLM (Groq / Gemini gratuits). Aucun appel payant."""
from __future__ import annotations

import json
import re
from typing import Any

import requests

from .config import Config


class LLMError(RuntimeError):
    pass


def _post(url: str, **kwargs) -> requests.Response:
    try:
        return requests.post(url, timeout=120, **kwargs)
    except requests.RequestException as exc:
        raise LLMError(f"Requete impossible: {exc}") from exc


def _groq(prompt: str, system: str, cfg: Config) -> str:
    resp = _post(
        "https://api.groq.com/openai/v1/chat/completions",
        headers={"Authorization": f"Bearer {cfg.groq_api_key}"},
        json={
            "model": cfg.groq_model,
            "temperature": 0.4,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": prompt},
            ],
            "response_format": {"type": "json_object"},
        },
    )
    if resp.status_code != 200:
        raise LLMError(f"Groq HTTP {resp.status_code}: {resp.text[:250]}")
    return resp.json()["choices"][0]["message"]["content"]


def _gemini(prompt: str, system: str, cfg: Config) -> str:
    url = (
        "https://generativelanguage.googleapis.com/v1beta/models/"
        f"{cfg.gemini_model}:generateContent?key={cfg.gemini_api_key}"
    )
    resp = _post(
        url,
        json={
            "system_instruction": {"parts": [{"text": system}]},
            "contents": [{"role": "user", "parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": 0.5, "responseMimeType": "application/json"},
        },
    )
    if resp.status_code != 200:
        raise LLMError(f"Gemini HTTP {resp.status_code}: {resp.text[:250]}")
    try:
        return resp.json()["candidates"][0]["content"]["parts"][0]["text"]
    except (KeyError, IndexError) as exc:
        raise LLMError("Reponse Gemini inattendue") from exc


def resolve_provider(cfg: Config) -> str:
    if cfg.provider != "auto":
        return cfg.provider
    if cfg.groq_api_key:
        return "groq"
    if cfg.gemini_api_key:
        return "gemini"
    return "offline"


def extract_json(raw: str) -> dict[str, Any]:
    text = re.sub(r"^```(?:json)?\s*", "", raw.strip())
    text = re.sub(r"\s*```$", "", text)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    start = text.find("{")
    if start == -1:
        raise LLMError(f"Aucun JSON dans la reponse: {text[:150]}")
    depth = 0
    for idx in range(start, len(text)):
        if text[idx] == "{":
            depth += 1
        elif text[idx] == "}":
            depth -= 1
            if depth == 0:
                return json.loads(text[start : idx + 1])
    raise LLMError("JSON incomplet.")


def chat_json(prompt: str, system: str, cfg: Config) -> dict[str, Any]:
    provider = resolve_provider(cfg)
    if provider == "groq":
        return extract_json(_groq(prompt, system, cfg))
    if provider == "gemini":
        return extract_json(_gemini(prompt, system, cfg))
    raise LLMError("Aucun LLM configure (GROQ_API_KEY ou GEMINI_API_KEY).")
