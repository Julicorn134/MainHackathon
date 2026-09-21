from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import ai_config
import store


@pytest.fixture(autouse=True)
def isolated_state(tmp_path, monkeypatch):
    monkeypatch.setattr(store, "STATE_PATH", tmp_path / "state.json")
    monkeypatch.setenv("BLOODSIGHT_DB", str(tmp_path / "records.sqlite3"))
    monkeypatch.setattr(ai_config, "SECRETS_PATH", tmp_path / "no-secrets.toml")
    for key in ("AI_PROVIDER", "OPENAI_API_KEY", "OPENAI_MODEL", "OPENROUTER_API_KEY", "OPENROUTER_MODEL"):
        monkeypatch.delenv(key, raising=False)
    monkeypatch.setenv("BLOODSIGHT_DATA_BACKEND", "sqlite")
    for key in ("SUPABASE_URL", "SUPABASE_SECRET_KEY", "SUPABASE_SERVICE_ROLE_KEY"):
        monkeypatch.delenv(key, raising=False)


@pytest.fixture
def history_csv():
    import pandas as pd
    df = pd.DataFrame({"date": pd.date_range("2026-01-01", periods=70), "blood_type": "O-",
                       "donations": 10, "demand": 12, "inventory": 160, "holiday": False})
    return df.to_csv(index=False).encode()


@pytest.fixture
def report():
    return {"lab_code": "BL-4790", "date": "2026-09-21", "blood_type": "O-",
            "lab": "Synthetic test lab", "urgent": False,
            "values": [{"key": "ferritin", "name": "Ferritin", "unit": "ng/mL",
                        "value": 33, "low": 30, "high": 300}]}
