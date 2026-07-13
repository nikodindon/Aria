"""
core/brain.py — Interface avec le LLM (Hermes / local)
"""
import os
import requests
from dotenv import load_dotenv

load_dotenv()

HERMES_URL = os.getenv("HERMES_API_URL", "http://localhost:8080/v1")
HERMES_MODEL = os.getenv("HERMES_MODEL", "default")
HERMES_API_KEY = os.getenv("HERMES_API_KEY", "")


def chat(messages: list[dict], system: str = "", max_tokens: int = 512) -> str:
    """
    Envoie une conversation au LLM et retourne la réponse texte.
    messages = [{"role": "user"|"assistant", "content": "..."}]
    system est injecté comme premier message role=system (standard OpenAI).
    """
    msgs = list(messages)
    if system:
        # Évite les doublons si l'appelant a déjà mis un system
        if not msgs or msgs[0].get("role") != "system":
            msgs = [{"role": "system", "content": system}] + msgs
        else:
            msgs[0] = {"role": "system", "content": system}

    payload = {
        "model": HERMES_MODEL,
        "max_tokens": max_tokens,
        "messages": msgs,
    }

    headers = {"Content-Type": "application/json"}
    if HERMES_API_KEY:
        headers["Authorization"] = f"Bearer {HERMES_API_KEY}"

    resp = requests.post(f"{HERMES_URL}/chat/completions", json=payload, headers=headers, timeout=60)
    resp.raise_for_status()
    data = resp.json()
    return data["choices"][0]["message"]["content"].strip()


def complete(prompt: str, max_tokens: int = 256) -> str:
    """Completion simple (non-chat)."""
    return chat([{"role": "user", "content": prompt}], max_tokens=max_tokens)
