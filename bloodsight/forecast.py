"""BloodSight AI: synthetic blood-bank data, 14-day forecast, shortage risk, campaign logic.

Run `python forecast.py` to (re)generate data.csv. Everything here is synthetic
and for demonstration only.
"""

from __future__ import annotations

import math
import sys
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.linear_model import Ridge

DATA_PATH = Path(__file__).with_name("data.csv")

HISTORY_DAYS = 180
HORIZON = 14
TRAIN_DAYS = 42          # the model learns from the most recent 6 weeks
SAFETY_DAYS = 3          # safety threshold = 3 days of supply
WARNING_DAYS = 5         # warning threshold = 5 days of supply
CAMPAIGN_LEAD_DAYS = 4   # outreach ramp-up + testing/processing before units are usable

# Public holidays (donor turnout drops). 2026 dates, plus early 2027.
HOLIDAYS = {
    date(2026, 1, 1), date(2026, 4, 3), date(2026, 4, 6), date(2026, 5, 1),
    date(2026, 5, 14), date(2026, 5, 25), date(2026, 10, 3), date(2026, 12, 25),
    date(2026, 12, 26), date(2027, 1, 1),
}

# Day-of-week shape, Monday..Sunday. Demand follows scheduled surgery (weekday-heavy);
# donations follow donor-centre opening hours (weak Sunday).
DEMAND_DOW = np.array([1.08, 1.12, 1.10, 1.08, 1.02, 0.82, 0.78])
DONATION_DOW = np.array([1.00, 1.05, 1.10, 1.10, 1.15, 0.95, 0.65])
HOLIDAY_DONATION_FACTOR = 0.45


@dataclass(frozen=True)
class TypeProfile:
    demand: float          # average units used per day
    supply_days: float     # inventory level the bank normally steers toward
    demand_drift: float    # relative demand change ramped in over the last DRIFT_DAYS
    donation_drift: float  # relative donation change ramped in over the last DRIFT_DAYS


DRIFT_DAYS = 21

# O- is the intentional demo scenario: universal-donor demand creeps up while
# donations sag, so stock is fine today but heading for a shortage.
PROFILES: dict[str, TypeProfile] = {
    "O+":  TypeProfile(97, 12.5, 0.00, 0.00),
    "O-":  TypeProfile(30, 12.5, 0.30, -0.30),
    "A+":  TypeProfile(76, 12.0, 0.00, 0.00),
    "A-":  TypeProfile(19, 8.0, 0.06, -0.06),
    "B+":  TypeProfile(22, 13.0, 0.00, 0.00),
    "B-":  TypeProfile(7, 8.5, 0.08, -0.08),
    "AB+": TypeProfile(11, 14.0, 0.00, 0.00),
    "AB-": TypeProfile(4, 7.5, 0.06, -0.06),
}
BLOOD_TYPES = list(PROFILES)


# --------------------------------------------------------------------------- data

def generate_data(end: date | None = None, seed: int = 7) -> pd.DataFrame:
    """Simulate HISTORY_DAYS of daily donations, demand and closing inventory."""
    end = end or date.today()
    days = [end - timedelta(days=HISTORY_DAYS - 1 - i) for i in range(HISTORY_DAYS)]
    dow = np.array([d.weekday() for d in days])
    holiday = np.array([d in HOLIDAYS for d in days])
    ramp = np.clip((np.arange(HISTORY_DAYS) - (HISTORY_DAYS - DRIFT_DAYS)) / DRIFT_DAYS, 0, 1)
    # Mild seasonal swing in donor turnout: lowest in mid-summer, highest in mid-winter.
    season = np.array([1 - 0.03 * math.cos(2 * math.pi * (d.timetuple().tm_yday - 196) / 365) for d in days])

    rows = []
    for k, (bt, p) in enumerate(PROFILES.items()):
        rng = np.random.default_rng([seed, k])  # independent stream per type: tuning one leaves the rest unchanged
        target = p.demand * p.supply_days
        demand_mean = p.demand * DEMAND_DOW[dow] * (1 + p.demand_drift * ramp)
        # Unexpected demand spikes (trauma, major surgery days): ~2 % of days.
        spikes = np.where(rng.random(HISTORY_DAYS) < 0.02, rng.uniform(1.4, 1.9, HISTORY_DAYS), 1.0)
        spikes[-10:] = 1.0  # keep the demo window clean
        demand = rng.poisson(demand_mean * spikes)

        donation_base = (p.demand * DONATION_DOW[dow] * season
                         * np.where(holiday, HOLIDAY_DONATION_FACTOR, 1.0)
                         * (1 + p.donation_drift * ramp))
        inv = target
        for i, d in enumerate(days):
            # Routine collection planning nudges stock back toward target; it is
            # too slow to absorb the recent drift, which is what the demo shows.
            slack = (1 - ramp[i]) if p.demand_drift else 1.0
            response = 1 + 1.0 * np.clip((target - inv) / target, -0.3, 0.3) * slack
            donated = rng.poisson(max(donation_base[i] * response, 0.1))
            inv = max(inv + donated - demand[i], 0)
            rows.append((d, bt, int(donated), int(demand[i]), int(inv), bool(holiday[i])))

    return pd.DataFrame(rows, columns=["date", "blood_type", "donations", "demand", "inventory", "holiday"])


def load_data() -> pd.DataFrame:
    if not DATA_PATH.exists():
        generate_data().to_csv(DATA_PATH, index=False)
    df = pd.read_csv(DATA_PATH, parse_dates=["date"])
    return df.sort_values(["blood_type", "date"]).reset_index(drop=True)


# ----------------------------------------------------------------------- forecast

def _features(dates: pd.DatetimeIndex, origin: pd.Timestamp) -> np.ndarray:
    dow = np.eye(7)[dates.weekday]
    trend = ((dates - origin).days.to_numpy() / 7.0).reshape(-1, 1)   # in weeks
    hol = np.array([d.date() in HOLIDAYS for d in dates], dtype=float).reshape(-1, 1)
    return np.hstack([dow, trend, hol])


def _fit_predict(series: pd.Series, future: pd.DatetimeIndex) -> tuple[np.ndarray, float]:
    """Ridge regression on day-of-week + trend + holiday; returns forecast and residual sd."""
    train = series.iloc[-TRAIN_DAYS:]
    origin = train.index[0]
    model = Ridge(alpha=1.0)
    x = _features(train.index, origin)
    model.fit(x, train.to_numpy())
    resid_sd = float(np.std(train.to_numpy() - model.predict(x), ddof=1))
    return np.clip(model.predict(_features(future, origin)), 0, None), resid_sd


def forecast_type(df: pd.DataFrame, blood_type: str, horizon: int = HORIZON) -> pd.DataFrame:
    """Projected inventory = current inventory + predicted donations - predicted demand."""
    s = df[df.blood_type == blood_type].set_index("date")
    future = pd.date_range(s.index[-1] + pd.Timedelta(days=1), periods=horizon)
    demand, sd_dem = _fit_predict(s.demand, future)
    donations, sd_don = _fit_predict(s.donations, future)
    inventory = s.inventory.iloc[-1] + np.cumsum(donations - demand)
    # Daily errors accumulate in a running balance: band widens with sqrt(days ahead).
    band = 1.28 * math.hypot(sd_dem, sd_don) * np.sqrt(np.arange(1, horizon + 1))
    return pd.DataFrame({
        "date": future, "demand": demand, "donations": donations, "raw": inventory, "band": band,
        "inventory": np.clip(inventory, 0, None),
        "low": np.clip(inventory - band, 0, None), "high": np.clip(inventory + band, 0, None),
    })


def thresholds(df: pd.DataFrame, blood_type: str) -> tuple[int, int]:
    """Safety / warning stock levels as days of supply at the 90-day average usage."""
    usage = df[df.blood_type == blood_type].demand.iloc[-90:].mean()
    rnd = 10 if usage >= 15 else 5
    return (int(round(usage * SAFETY_DAYS / rnd) * rnd), int(round(usage * WARNING_DAYS / rnd) * rnd))


def apply_campaign(fc: pd.DataFrame, extra_units: int, start_day: int, window: int) -> pd.DataFrame:
    """Spread extra donations evenly over `window` days, first usable on `start_day` (1-based)."""
    out = fc.copy()
    boost = np.zeros(len(fc))
    last = min(start_day - 1 + window, len(fc))
    if extra_units > 0 and last > start_day - 1:
        boost[start_day - 1:last] = extra_units / window
    raw = out["raw"] + np.cumsum(boost)
    out["raw"] = raw
    out["inventory"] = raw.clip(lower=0)
    out["low"] = (raw - out["band"]).clip(lower=0)
    out["high"] = (raw + out["band"]).clip(lower=0)
    out["donations"] = out["donations"] + boost
    return out


def assess(fc: pd.DataFrame, safety: int, warning: int) -> dict:
    inv = fc.inventory.to_numpy()
    below_safety = np.flatnonzero(inv < safety)
    below_warning = np.flatnonzero(inv < warning)
    if below_safety.size:
        risk = "Critical"
    elif below_warning.size:
        risk = "Medium"
    else:
        risk = "Low"
    return {
        "risk": risk,
        # Outcome at the end of the horizon: a campaign cannot undo a dip that happens
        # before its units arrive, so interventions are judged on shortage + recovery.
        "outcome": "Critical" if risk == "Critical" else ("Low" if inv[-1] >= warning else "Medium"),
        "end_inventory": float(inv[-1]),
        "min_inventory": float(inv.min()),
        "day7_inventory": float(inv[6]),
        "days_to_safety": int(below_safety[0]) + 1 if below_safety.size else None,
        "days_to_warning": int(below_warning[0]) + 1 if below_warning.size else None,
    }


def recommend(df: pd.DataFrame, blood_type: str, fc: pd.DataFrame, safety: int, warning: int,
              window: int = 5) -> dict:
    """Turn the forecast into an intervention: how many units, by when, and why."""
    a = assess(fc, safety, warning)
    s = df[df.blood_type == blood_type]
    recent, prior = s.iloc[-14:], s.iloc[-42:-14]
    demand_change = recent.demand.mean() / prior.demand.mean() - 1
    donation_change = recent.donations.mean() / prior.donations.mean() - 1
    upcoming_holidays = [d for d in fc.date if d.date() in HOLIDAYS]

    # Size the campaign by simulation: smallest launch-today campaign that avoids a shortage
    # and ends the horizon above the warning level; failing that, one that avoids a shortage.
    target_units, risk_after = 0, a["risk"]
    if a["risk"] != "Low":
        trials = [(u, assess(apply_campaign(fc, u, CAMPAIGN_LEAD_DAYS + 1, window), safety, warning)["outcome"])
                  for u in range(10, 610, 10)]
        for goal in (("Low",), ("Low", "Medium")):
            hit = next(((u, r) for u, r in trials if r in goal), None)
            if hit:
                target_units, risk_after = hit
                break
        else:
            target_units, risk_after = trials[-1]
    breach = a["days_to_safety"] or a["days_to_warning"]
    launch_within_days = max(breach - CAMPAIGN_LEAD_DAYS, 0) if breach else None

    drivers = []
    if abs(demand_change) >= 0.04:
        drivers.append(f"Usage is {'up' if demand_change > 0 else 'down'} {abs(demand_change):.0%} "
                       "over the last 2 weeks versus the 4 weeks before.")
    if abs(donation_change) >= 0.04:
        drivers.append(f"Donations are {'up' if donation_change > 0 else 'down'} {abs(donation_change):.0%} "
                       "over the same period.")
    for d in upcoming_holidays:
        drivers.append(f"Public holiday on {d:%a %d %b}: donor turnout typically drops by about "
                       f"{1 - HOLIDAY_DONATION_FACTOR:.0%}.")
    if not drivers:
        drivers.append("Usage and donations are in line with the recent baseline.")

    return {**a, "target_units": target_units, "risk_after": risk_after, "window": window,
            "launch_within_days": launch_within_days,
            "priority": {"Critical": "High", "Medium": "Moderate", "Low": "None"}[a["risk"]],
            "drivers": drivers, "demand_change": demand_change, "donation_change": donation_change}


def backtest(df: pd.DataFrame, blood_type: str, horizon: int = HORIZON) -> float:
    """Hold out the last `horizon` days and report total-demand forecast error (%)."""
    s = df[df.blood_type == blood_type].set_index("date")
    train, test = s.iloc[:-horizon], s.iloc[-horizon:]
    pred, _ = _fit_predict(train.demand, test.index)
    return float(abs(pred.sum() - test.demand.sum()) / test.demand.sum())


def summary_table(df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for bt in BLOOD_TYPES:
        safety, warning = thresholds(df, bt)
        a = assess(forecast_type(df, bt), safety, warning)
        s = df[df.blood_type == bt]
        rows.append({
            "blood_type": bt, "inventory": int(s.inventory.iloc[-1]),
            "days_of_supply": s.inventory.iloc[-1] / s.demand.iloc[-14:].mean(),
            "projected_min": int(round(a["min_inventory"])), "safety": safety, "warning": warning,
            "risk": a["risk"], "days_to_safety": a["days_to_safety"],
        })
    return pd.DataFrame(rows)


if __name__ == "__main__":
    end = date.fromisoformat(sys.argv[1]) if len(sys.argv) > 1 else date.today()
    data = generate_data(end)
    data.to_csv(DATA_PATH, index=False)
    print(f"Wrote {len(data)} rows to {DATA_PATH.name} (through {end})")
    print(summary_table(load_data()).to_string(index=False))
