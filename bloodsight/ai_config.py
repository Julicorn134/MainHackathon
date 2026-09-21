"""Read secrets locally. Never render or log API keys."""
import os
import tomllib
from pathlib import Path

SECRETS_PATH = Path(__file__).parent / ".streamlit" / "secrets.toml"


def read_secrets() -> dict:
    local = {}
    if SECRETS_PATH.exists():
        try:
            local = tomllib.loads(SECRETS_PATH.read_text(encoding="utf-8-sig"))
        except (OSError, tomllib.TOMLDecodeError):
            raise ValueError("Settings could not be read. Check .streamlit/secrets.toml syntax.") from None
    return local


def settings() -> dict:
    local = read_secrets()

    def get(name, default=""):
        return str(os.environ.get(name) or local.get(name) or default).strip()

    provider = get("AI_PROVIDER", "openrouter" if get("OPENROUTER_API_KEY") else "openai").lower()
    if provider not in ("openai", "openrouter"):
        raise ValueError("Set AI_PROVIDER to openrouter or openai in server settings.")
    router = provider == "openrouter"
    key_name = "OPENROUTER_API_KEY" if router else "OPENAI_API_KEY"
    key = get(key_name)
    if not router and key.startswith("sk-or-"):
        raise ValueError("This is an OpenRouter key. Set AI_PROVIDER=openrouter and use OPENROUTER_API_KEY.")
    return {
        "provider": provider,
        "provider_label": "OpenRouter" if router else "OpenAI",
        "api_key": key,
        "key_name": key_name,
        "base_url": "https://openrouter.ai/api/v1" if router else "https://api.openai.com/v1",
        "model": get("OPENROUTER_MODEL", "openai/gpt-4.1-mini") if router else get("OPENAI_MODEL", "gpt-4.1-mini"),
    }
