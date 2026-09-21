"""Read secrets locally. Never render or log API keys."""
import os
import tomllib
from pathlib import Path

SECRETS_PATH = Path(__file__).parent / ".streamlit" / "secrets.toml"


def settings() -> dict:
    local = {}
    if SECRETS_PATH.exists():
        try:
            local = tomllib.loads(SECRETS_PATH.read_text(encoding="utf-8-sig"))
        except (OSError, tomllib.TOMLDecodeError):
            raise ValueError("AI settings could not be read. Check .streamlit/secrets.toml syntax.") from None
    return {
        "api_key": str(os.environ.get("OPENAI_API_KEY") or local.get("OPENAI_API_KEY") or "").strip(),
        "model": str(os.environ.get("OPENAI_MODEL") or local.get("OPENAI_MODEL") or "gpt-4.1-mini").strip(),
    }
