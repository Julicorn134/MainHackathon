"""Choose an explicit dataset and reject series unsuitable for a daily model."""
import pandas as pd

import data_store
import forecast
import store

MIN_HISTORY = 42


def load(username: str, source: str) -> pd.DataFrame:
    user = store.get_user(username)
    if not user or user["role"] != "centre":
        raise ValueError("Forecast data is available to centre staff only.")
    if source == "uploaded":
        df = data_store.history_for(username)
    elif source == "demo":
        df = forecast.load_data()
    else:
        raise ValueError("Select uploaded data or the demonstration dataset.")
    df.attrs["source"] = source
    return df


def quality(df: pd.DataFrame) -> list[dict]:
    rows = []
    for bt in forecast.BLOOD_TYPES:
        s = df[df.blood_type == bt].sort_values("date")
        if s.empty:
            continue
        days = pd.DatetimeIndex(s.date)
        gaps = max(0, (days[-1] - days[0]).days + 1 - len(days.unique()))
        duplicate = days.has_duplicates
        ready = len(s) >= MIN_HISTORY and not gaps and not duplicate
        rows.append(dict(blood_type=bt, days=len(s), first_date=days[0].date().isoformat(),
                         last_date=days[-1].date().isoformat(), missing_days=gaps, ready=ready,
                         reason="Ready" if ready else "Dates repeat" if duplicate else
                         f"{gaps} missing days" if gaps else f"Needs {MIN_HISTORY - len(s)} more daily rows"))
    return rows


def ready_data(df: pd.DataFrame) -> pd.DataFrame:
    eligible = [r["blood_type"] for r in quality(df) if r["ready"]]
    return df[df.blood_type.isin(eligible)].copy()
