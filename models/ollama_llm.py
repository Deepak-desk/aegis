"""
AEGIS — Ollama LLM Interface
Handles all communication with the local Qwen model via Ollama.
"""

import requests

OLLAMA_URL = "http://localhost:11434/api/generate"
DEFAULT_MODEL = "gemma4:e4b"


def query_llm(
    prompt: str,
    system: str = "",
    model: str = DEFAULT_MODEL,
    temperature: float = 0.3,
    max_tokens: int = 512,
) -> str:
    """Send a prompt to Qwen via Ollama and return the response text."""
    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "options": {
            "temperature": temperature,
            "top_p": 0.9,
            "num_predict": max_tokens,
        },
    }
    if system:
        payload["system"] = system

    try:
        response = requests.post(OLLAMA_URL, json=payload, timeout=120)
        response.raise_for_status()
        return response.json().get("response", "Error: No response from model.")
    except requests.ConnectionError:
        return "❌ Cannot connect to Ollama. Make sure it is running (`ollama serve`)."
    except requests.Timeout:
        return "❌ Ollama request timed out."
    except Exception as e:
        return f"❌ Error: {e}"
