"""Shared data layer for BloodSight AI: accounts, requests, bookings, notifications, lab results.

One JSON file (state.json) holds everything that changes. Seed data (places, lab reports,
donation history, a synthetic population for donor matching) lives in this module.
Set the BLOODSIGHT_STATE environment variable to use a different state file (tests, parallel work).

Privacy rules this layer enforces (from the design):
1. Nobody is asked unless they switched it on; pause or a per-place switch stops it.
2. A place sees counts. It sees a name only when that person books a slot.
3. "Not this time" is stored as a count input only and is never exposed by name.
4. At most MAX_ASKS_PER_MONTH requests per person per month.
5. Urgent lab values are held back until the doctor has phoned.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import secrets
from datetime import date, datetime, timedelta
from functools import lru_cache
from pathlib import Path

import numpy as np

STATE_PATH = Path(os.environ.get("BLOODSIGHT_STATE") or Path(__file__).with_name("state.json"))
DATA_PATH = Path(__file__).with_name("data.csv")

BLOOD_TYPES = ["O+", "O-", "A+", "A-", "B+", "B-", "AB+", "AB-"]
ANY_TYPE = "plasma (any type)"
MAX_ASKS_PER_MONTH = 2
MIN_DAYS_BETWEEN_DONATIONS = 56
EXPECTED_BOOKING_RATE = 0.09  # from earlier requests: about 9 in 100 asked people book

PLACES = {
    "rbc": {"name": "Regional Blood Centre", "kind": "blood centre"},
    "mumc": {"name": "MUMC+ hospital", "kind": "hospital"},
    "heerlen": {"name": "Donor centre Heerlen", "kind": "donor centre"},
}
LAB_NAME = "Bloodlab Maastricht"


# ------------------------------------------------------------------------- clock

@lru_cache(maxsize=1)
def today() -> date:
    """The demo's "today" is the last day of the dataset, so every screen agrees with the forecast."""
    with open(DATA_PATH, encoding="utf-8") as f:
        return date.fromisoformat(max(line.split(",")[0][:10] for line in f.readlines()[1:]))


def _stamp() -> str:
    return f"{today().isoformat()} {datetime.now():%H:%M:%S}"


# ------------------------------------------------------------------- lab reports

# name, unit, low, high, typical value
_ANALYTES = [
    ("ferritin", "Ferritin (iron store)", "ng/mL", 30, 300, 85),
    ("ldl", "LDL cholesterol", "mmol/L", 0, 3.0, 2.6),
    ("hb", "Haemoglobin", "g/dL", 12.0, 17.5, 14.1),
    ("tsh", "Thyroid (TSH)", "mU/L", 0.4, 4.0, 2.1),
    ("wbc", "White blood cells", "10^9/L", 4.0, 10.0, 6.2),
    ("plt", "Platelets", "10^9/L", 150, 400, 251),
    ("rbc_count", "Red blood cells", "10^12/L", 4.0, 5.9, 4.8),
    ("mcv", "MCV (red cell size)", "fL", 80, 100, 89),
    ("glucose", "Glucose (fasting)", "mmol/L", 3.9, 5.6, 5.0),
    ("hba1c", "HbA1c", "mmol/mol", 20, 42, 35),
    ("hdl", "HDL cholesterol", "mmol/L", 1.0, 3.0, 1.5),
    ("trig", "Triglycerides", "mmol/L", 0, 1.7, 1.1),
    ("creat", "Creatinine", "umol/L", 45, 110, 78),
    ("egfr", "eGFR (kidney function)", "mL/min", 60, 200, 96),
    ("alt", "ALT (liver)", "U/L", 0, 45, 24),
    ("crp", "CRP (inflammation)", "mg/L", 0, 5, 1.2),
    ("b12", "Vitamin B12", "pmol/L", 140, 650, 380),
    ("vitd", "Vitamin D", "nmol/L", 50, 150, 72),
]


def _report(report_id: str, day: str, blood_type: str, overrides: dict | None = None) -> dict:
    values = []
    for line, (key, name, unit, low, high, typical) in enumerate(_ANALYTES, start=1):
        v = (overrides or {}).get(key, typical)
        flag = "Low" if v < low else "High" if v > high else "In range"
        values.append({"key": key, "name": name, "value": v, "unit": unit, "low": low, "high": high,
                       "flag": flag, "line": line if key != "ferritin" else 7})
    return {"id": report_id, "date": day, "lab": LAB_NAME, "blood_type": blood_type, "values": values}


# Reports per lab code. The 14 Sep reports sit in the batch of 21 Sep and are invisible until published.
REPORTS = {
    "BL-4790": [_report("R-4790-1", "2026-02-12", "O-", {"ferritin": 41, "ldl": 3.6}),
                _report("R-4790-2", "2026-06-03", "O-", {"ferritin": 33, "ldl": 3.8}),
                _report("R-4790-3", "2026-09-14", "O-", {"ferritin": 18, "ldl": 3.9})],
    "BL-4802": [_report("R-4802-1", "2026-03-20", "A+", {"vitd": 44}),
                _report("R-4802-2", "2026-09-14", "A+", {"vitd": 58})],
    "BL-4821": [_report("R-4821-1", "2026-09-14", "O-", {"ferritin": 64})],
    "BL-4835": [_report("R-4835-1", "2026-09-14", "B+", {"ldl": 3.4})],
}
BATCH_ID = "2026-09-21"
BATCH_REPORT_IDS = ["R-4790-3", "R-4802-2", "R-4821-1", "R-4835-1"]
# The batch as the lab system delivers it: 212 reports, 205 ready, 7 held back.
BATCH_TOTALS = {"reports": 212, "ready": 205, "donor_link": 38}
BATCH_HELD = [
    {"code": "BL-4907", "detail": "potassium 6.4 mmol/L", "reason": "urgent", "note": "Urgent: doctor is phoned first"},
    {"code": "BL-4911", "detail": "haemoglobin 7.2 g/dL", "reason": "urgent", "note": "Urgent: doctor is phoned first"},
    {"code": "BL-4933", "detail": "sodium 121 mmol/L", "reason": "urgent", "note": "Urgent: doctor is phoned first"},
    {"code": "BL-4950", "detail": "glucose 24.8 mmol/L", "reason": "urgent", "note": "Urgent: doctor is phoned first"},
    {"code": "BL-5103", "detail": "name on sample differs", "reason": "mismatch", "note": "Check by hand"},
    {"code": "BL-5117", "detail": "date of birth differs", "reason": "mismatch", "note": "Check by hand"},
    {"code": "BL-5140", "detail": "lab code unreadable", "reason": "mismatch", "note": "Check by hand"},
]

# Past donations per lab code (where it went). Total/places are the lifetime figures shown on the screen.
DONATIONS = {
    "BL-4790": {"total": 7, "places": 3, "history": [
        {"date": "2026-07-03", "kind": "whole blood", "place": "rbc", "used": "Used on Thu 9 Jul at MUMC+ hospital"},
        {"date": "2026-02-12", "kind": "plasma", "place": "heerlen", "used": "Used in March, for medicine"},
        {"date": "2025-11-03", "kind": "whole blood", "place": "rbc", "used": "Used on Sat 8 Nov at MUMC+ hospital"},
    ]},
}

# ---------------------------------------------------------------------- accounts


def _hash(password: str, salt: str) -> str:
    return hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt), 50_000).hex()


def _account(password: str, **fields) -> dict:
    salt = secrets.token_hex(8)
    return {"salt": salt, "password_hash": _hash(password, salt), **fields}


def _patient(password, name, lab_code, blood_type, postcode, distances, switches, places=None, asked=0):
    return _account(password, role="patient", name=name, lab_code=lab_code, blood_type=blood_type,
                    postcode=postcode, distances=distances, switches=switches, paused=False,
                    places=places or {}, asked_this_month=asked)


def _seed() -> dict:
    t = today()
    week = [(t + timedelta(days=d)).isoformat() for d in range(1, 6)]
    return {
        "users": {
            "centre": _account("centre123", role="centre", name="Robin Vos", org="rbc",
                               title="Regional Blood Centre"),
            "lab": _account("lab123", role="lab", name="Dr. Imke Peters", org="lab", title=LAB_NAME),
            "patient": _patient("patient123", "Alex Jansen", "BL-4790", "O-", "6211",
                                {"rbc": 2.1, "mumc": 3.4, "heerlen": 24.0},
                                {"results": True, "nearby": True, "gave_before": True},
                                places={"rbc": True, "heerlen": True}),
            "patient2": _patient("patient123", "Sam de Boer", "BL-4802", "A+", "6224",
                                 {"rbc": 5.8, "mumc": 4.9, "heerlen": 27.0},
                                 {"results": True, "nearby": False, "gave_before": False}),
        },
        # Two needs from other places are already open, so the patient's Needs tab is not empty on day one.
        "requests": [
            {"id": "REQ-1", "place": "mumc", "blood_type": "O-", "radius_km": 25, "urgency": "This week",
             "slots": [f"{week[1]} 10:00", f"{week[2]} 14:30", f"{week[3]} 08:45"], "target": 60,
             "message": "MUMC+ hospital needs O- blood this week for planned surgery.",
             "status": "sent", "created_by": "system", "sent_at": f"{t.isoformat()} 08:00:00", "day": 1,
             "matched": {"total": 640, "patients": 300, "gave_before": 340}},
            {"id": "REQ-2", "place": "heerlen", "blood_type": ANY_TYPE, "radius_km": 50, "urgency": "This month",
             "slots": [f"{week[2]} 11:00", f"{week[4]} 09:30"], "target": 120,
             "message": "Donor centre Heerlen needs plasma donors this month. Any blood type can give plasma.",
             "status": "sent", "created_by": "system", "sent_at": f"{t.isoformat()} 08:00:00", "day": 1,
             "matched": {"total": 1310, "patients": 0, "gave_before": 1310}},
        ],
        "bookings": [],
        "declines": [],       # {"request": id, "username": ...}; only ever read as a count
        "notifications": [],
        "lab": {"published_batches": [], "released": [], "phoned": []},
        "counter": 2,
    }


def load() -> dict:
    if not STATE_PATH.exists():
        save(_seed())
    return json.loads(STATE_PATH.read_text(encoding="utf-8"))


def save(state: dict) -> None:
    tmp = STATE_PATH.with_suffix(".tmp")
    tmp.write_text(json.dumps(state, indent=1), encoding="utf-8")
    tmp.replace(STATE_PATH)


def reset() -> None:
    """Back to the seeded demo state."""
    save(_seed())


def _public(username: str, u: dict) -> dict:
    return {"username": username, **{k: v for k, v in u.items() if k not in ("salt", "password_hash")}}


def authenticate(username: str, password: str) -> dict | None:
    username = username.strip().lower()
    u = load()["users"].get(username)
    if u and hmac.compare_digest(u["password_hash"], _hash(password, u["salt"])):
        return _public(username, u)
    return None


def get_user(username: str) -> dict | None:
    u = load()["users"].get(username)
    return _public(username, u) if u else None


def update_user(username: str, **fields) -> dict:
    """Change profile fields: switches, paused, places, postcode, blood_type."""
    state = load()
    u = state["users"][username]
    for k, v in fields.items():
        if k in ("switches", "places") and isinstance(v, dict):
            u.setdefault(k, {}).update(v)
        elif k in ("paused", "postcode", "blood_type", "name"):
            u[k] = v
    save(state)
    return _public(username, u)


def unclaimed_lab_codes() -> list[str]:
    claimed = {u.get("lab_code") for u in load()["users"].values()}
    return [c for c in REPORTS if c not in claimed]


def register_patient(lab_code: str, username: str, password: str, name: str, postcode: str,
                     blood_type: str | None, switches: dict) -> dict:
    """First open: the lab code ties the account to one patient. Raises ValueError with a readable reason."""
    lab_code, username = lab_code.strip().upper(), username.strip().lower()
    state = load()
    if lab_code not in REPORTS:
        raise ValueError("This lab code is not known. It is printed on your lab letter, e.g. BL-4821.")
    if any(u.get("lab_code") == lab_code for u in state["users"].values()):
        raise ValueError("This lab code already has an account.")
    if not username or username in state["users"]:
        raise ValueError("This username is taken.")
    if len(password) < 6:
        raise ValueError("Use a password of at least 6 characters.")
    # Distances are derived from the postcode in a real system; the demo draws stable pseudo-distances.
    if not blood_type and BATCH_ID in state["lab"]["published_batches"]:
        blood_type = REPORTS[lab_code][-1]["blood_type"]  # unknown: the published lab result fills it in
    rng = np.random.default_rng(int(hashlib.sha256(postcode.strip().encode()).hexdigest()[:8], 16))
    distances = {"rbc": round(float(rng.uniform(1, 9)), 1), "mumc": round(float(rng.uniform(1, 9)), 1),
                 "heerlen": round(float(rng.uniform(18, 30)), 1)}
    state["users"][username] = _patient(password, name.strip() or username, lab_code, blood_type, postcode.strip(),
                                        distances, {"results": True, "nearby": False, "gave_before": False, **switches})
    save(state)
    return _public(username, state["users"][username])


# ----------------------------------------------------------------- notifications

def notify(to: str, kind: str, title: str, body: str, sender: str, ref: str | None = None,
           state: dict | None = None) -> None:
    """kind: need | results | message | booking. Pass `state` to batch several writes into one save."""
    own = state is None
    state = state or load()
    state["counter"] += 1
    state["notifications"].append({"id": f"N-{state['counter']}", "to": to, "kind": kind, "title": title,
                                   "body": body, "from": sender, "ref": ref, "created_at": _stamp(), "read": False})
    if own:
        save(state)


def notifications(username: str, unread_only: bool = False) -> list[dict]:
    items = [n for n in load()["notifications"] if n["to"] == username and not (unread_only and n["read"])]
    return sorted(items, key=lambda n: n["created_at"], reverse=True)


def unread_count(username: str) -> int:
    return len(notifications(username, unread_only=True))


def mark_read(username: str, notification_id: str | None = None) -> None:
    state = load()
    for n in state["notifications"]:
        if n["to"] == username and (notification_id is None or n["id"] == notification_id):
            n["read"] = True
    save(state)


def patients(state: dict | None = None) -> list[dict]:
    """The lab's patients (the lab knows its own patients by name)."""
    state = state or load()
    return [_public(name, u) for name, u in state["users"].items() if u["role"] == "patient"]


def send_message(sender_username: str, audience: str, title: str, body: str, to: str | None = None) -> int:
    """Staff-created notification. audience: all | donors | one. Returns how many people got it.

    'all' = every patient with the results switch on (they agreed to hear from the lab);
    'donors' = patients who switched the donor part on; 'one' = the patient in `to`.
    """
    state = load()
    sender = state["users"][sender_username]
    org = sender.get("title") or sender["name"]
    targets = []
    for p in patients(state):
        sw = p["switches"]
        if audience == "one" and p["username"] == to:
            targets.append(p)
        elif audience == "all" and sw.get("results"):
            targets.append(p)
        elif audience == "donors" and (sw.get("nearby") or sw.get("gave_before")) and not p.get("paused"):
            targets.append(p)
    for p in targets:
        notify(p["username"], "message", title, body, org, state=state)
    save(state)
    return len(targets)


# ------------------------------------------------------------- donor matching

@lru_cache(maxsize=1)
def _population() -> dict:
    """Synthetic people who are in the system: patients of the lab and people who gave before."""
    rng = np.random.default_rng(11)
    n = 120_000
    freq = [0.38, 0.07, 0.34, 0.06, 0.09, 0.02, 0.03, 0.01]
    return {
        "blood_type": rng.choice(len(BLOOD_TYPES), size=n, p=freq),
        "distance": rng.rayleigh(18.0, size=n),
        "consent": rng.random(n) < 0.60,
        "days_since": np.where(rng.random(n) < 0.35, 9999, rng.integers(5, 400, size=n)),
        "asked": rng.choice([0, 1, 2], size=n, p=[0.70, 0.25, 0.05]),
        "gave_here": rng.random(n) < 0.52,
    }


def match_count(blood_type: str, radius_km: float) -> dict:
    """How many people a request would reach. Counts only: the centre never gets names from this."""
    p = _population()
    m = (p["distance"] <= radius_km) & p["consent"] & (p["days_since"] >= MIN_DAYS_BETWEEN_DONATIONS) \
        & (p["asked"] < MAX_ASKS_PER_MONTH)
    if blood_type != ANY_TYPE:
        m &= p["blood_type"] == BLOOD_TYPES.index(blood_type)
    total, gave = int(m.sum()), int((m & p["gave_here"]).sum())
    return {"total": total, "gave_before": gave, "patients": total - gave,
            "expected_bookings": int(round(total * EXPECTED_BOOKING_RATE))}


def _last_donation_days(user: dict) -> int | None:
    hist = DONATIONS.get(user.get("lab_code"), {}).get("history", [])
    return (today() - date.fromisoformat(hist[0]["date"])).days if hist else None


def _gave_at(user: dict, place: str) -> str | None:
    for d in DONATIONS.get(user.get("lab_code"), {}).get("history", []):
        if d["place"] == place:
            return d["date"]
    return None


def _matches(user: dict, req: dict) -> list[str] | None:
    """Reasons this person sees this request, or None if they must not be asked."""
    sw, place = user["switches"], req["place"]
    if user.get("paused") or user.get("places", {}).get(place) is False:
        return None
    gave = _gave_at(user, place)
    near = user["distances"].get(place, 999) <= req["radius_km"]
    type_ok = req["blood_type"] == ANY_TYPE or user.get("blood_type") == req["blood_type"]
    by_near = sw.get("nearby") and near and type_ok
    by_gave = sw.get("gave_before") and gave and type_ok
    if not (by_near or by_gave):
        return None
    last = _last_donation_days(user)
    if last is not None and last < MIN_DAYS_BETWEEN_DONATIONS:
        return None
    reasons = []
    if type_ok and req["blood_type"] != ANY_TYPE:
        reasons.append(f"you are {user['blood_type']}")
    if near:
        reasons.append(f"you live {user['distances'][place]:g} km away")
    if gave:
        reasons.append(f"you gave here on {date.fromisoformat(gave):%d %b}".replace(" 0", " "))
    if last is not None:
        reasons.append(f"you last gave {last} days ago")
    return reasons


# ---------------------------------------------------------------------- requests

_SEEN = [0.68, 0.80, 0.86, 0.89, 0.90]
_BOOKED = [0.028, 0.052, 0.071, 0.083, 0.090]
_DECLINED = [0.031, 0.050, 0.062, 0.070, 0.075]
_FIRST = ["Lena", "Sam", "Noa", "Daan", "Emma", "Finn", "Sara", "Luuk", "Mila", "Jesse", "Eva", "Thijs"]
_LAST = "VKBJMSHRDWPG"


def requests(place: str | None = None, status: str | None = None) -> list[dict]:
    return [r for r in load()["requests"]
            if (place is None or r["place"] == place) and (status is None or r["status"] == status)]


def get_request(request_id: str) -> dict | None:
    return next((r for r in load()["requests"] if r["id"] == request_id), None)


def create_request(created_by: str, place: str, blood_type: str, radius_km: float, slots: list[str],
                   target: int, message: str, urgency: str = "Shortage forecast", send: bool = False) -> dict:
    """Save a request as a draft, or send it straight away. A staff member always presses send."""
    state = load()
    state["counter"] += 1
    req = {"id": f"REQ-{state['counter']}", "place": place, "blood_type": blood_type, "radius_km": radius_km,
           "urgency": urgency, "slots": slots, "target": int(target), "message": message, "status": "draft",
           "created_by": created_by, "sent_at": None, "day": 0, "matched": match_count(blood_type, radius_km)}
    state["requests"].append(req)
    save(state)
    return send_request(req["id"]) if send else req


def send_request(request_id: str) -> dict:
    """Send: every matching real account gets a 'need' notification and their monthly ask count goes up."""
    state = load()
    req = next(r for r in state["requests"] if r["id"] == request_id)
    req.update(status="sent", sent_at=_stamp(), day=1, matched=match_count(req["blood_type"], req["radius_km"]))
    for p in patients(state):
        if p.get("asked_this_month", 0) >= MAX_ASKS_PER_MONTH or _matches(p, req) is None:
            continue
        state["users"][p["username"]]["asked_this_month"] = p.get("asked_this_month", 0) + 1
        notify(p["username"], "need", f"{PLACES[req['place']]['name']} needs {req['blood_type']}",
               req["message"], PLACES[req["place"]]["name"], ref=req["id"], state=state)
    save(state)
    return req


def close_request(request_id: str, reason: str = "closed by staff") -> None:
    state = load()
    for r in state["requests"]:
        if r["id"] == request_id:
            r.update(status="closed", closed_reason=reason)
    save(state)


def advance_day(request_id: str) -> dict:
    """Demo control: move a sent request one day forward in its simulated response curve."""
    state = load()
    req = next(r for r in state["requests"] if r["id"] == request_id)
    if req["status"] == "sent" and req["day"] < len(_SEEN):
        req["day"] += 1
    save(state)
    if request_stats(request_id)["booked"] >= req["target"]:
        close_request(request_id, "target reached")
    return get_request(request_id)


def request_stats(request_id: str) -> dict:
    """asked / seen / booked / not this time. Simulated population answers plus the real accounts' answers."""
    state = load()
    req = next(r for r in state["requests"] if r["id"] == request_id)
    total = req["matched"]["total"]
    i = max(min(req["day"], len(_SEEN)) - 1, 0)
    sent = req["status"] != "draft"
    real_booked = sum(1 for b in state["bookings"] if b["request"] == request_id and b["status"] == "booked")
    real_declined = sum(1 for d in state["declines"] if d["request"] == request_id)
    return {"asked": total if sent else 0, "seen": int(total * _SEEN[i]) if sent else 0,
            "booked": (int(total * _BOOKED[i]) if sent else 0) + real_booked,
            "not_this_time": (int(total * _DECLINED[i]) if sent else 0) + real_declined,
            "target": req["target"], "day": req["day"], "simulated": sent}


def request_bookings(request_id: str, sample: int = 6) -> dict:
    """Bookings a place may see by name: real accounts that booked, plus a few simulated ones, plus a count."""
    state = load()
    req = next(r for r in state["requests"] if r["id"] == request_id)
    named = []
    for b in state["bookings"]:
        if b["request"] == request_id and b["status"] == "booked":
            u = state["users"][b["username"]]
            gave = _gave_at(u, req["place"])
            first, *rest = u["name"].split()
            named.append({"slot": b["slot"], "name": f"{first} {rest[-1][0]}." if rest else first,
                          "blood_type": u.get("blood_type"), "real": True,
                          "note": f"gave here {date.fromisoformat(gave):%d %b}".replace(" 0", " ") if gave
                          else "patient of the lab, first time"})
    stats = request_stats(request_id)
    simulated_total = stats["booked"] - len(named)
    rng = np.random.default_rng(int(request_id.split("-")[1]))
    for k in range(min(sample, simulated_total)):
        gave = rng.random() < 0.55
        named.append({"slot": req["slots"][k % len(req["slots"])] if req["slots"] else "",
                      "name": f"{_FIRST[int(rng.integers(len(_FIRST)))]} {_LAST[int(rng.integers(len(_LAST)))]}.",
                      "blood_type": req["blood_type"], "real": False,
                      "note": "gave here before" if gave else "patient of the lab, first time"})
    named.sort(key=lambda b: (not b["real"], b["slot"]))
    return {"named": named, "more": max(simulated_total - sample, 0), "total": stats["booked"]}


def expected_donations(place: str, blood_type: str) -> int:
    """Booked donations from open requests: feeds back into the outlook as expected donations."""
    return sum(request_stats(r["id"])["booked"] for r in requests(place, "sent") if r["blood_type"] == blood_type)


# ---------------------------------------------------------------- patient side

def needs_for(username: str) -> list[dict]:
    """Open requests this person may see, each with the reasons. No need, no card."""
    state = load()
    u = _public(username, state["users"][username])
    out = []
    for r in state["requests"]:
        if r["status"] != "sent":
            continue
        reasons = _matches(u, r)
        if reasons is None:
            continue
        mine = next((b for b in state["bookings"]
                     if b["request"] == r["id"] and b["username"] == username and b["status"] == "booked"), None)
        declined = any(d["request"] == r["id"] and d["username"] == username for d in state["declines"])
        out.append({**r, "place_name": PLACES[r["place"]]["name"], "distance_km": u["distances"].get(r["place"]),
                    "gave_here": _gave_at(u, r["place"]) is not None, "reasons": reasons,
                    "my_booking": mine, "declined": declined})
    order = {"Shortage forecast": 0, "This week": 1, "This month": 2}
    return sorted(out, key=lambda r: (order.get(r["urgency"], 3), r["distance_km"] or 999))


def book(username: str, request_id: str, slot: str) -> dict:
    """Book a slot. This is the moment the place learns a name."""
    state = load()
    req = next(r for r in state["requests"] if r["id"] == request_id)
    if req["status"] != "sent":
        raise ValueError("This request is closed.")
    state["bookings"] = [b for b in state["bookings"]
                         if not (b["request"] == request_id and b["username"] == username)]
    state["declines"] = [d for d in state["declines"]
                         if not (d["request"] == request_id and d["username"] == username)]
    state["counter"] += 1
    booking = {"id": f"B-{state['counter']}", "request": request_id, "username": username, "slot": slot,
               "place": req["place"], "status": "booked", "created_at": _stamp()}
    state["bookings"].append(booking)
    name = state["users"][username]["name"]
    place = PLACES[req["place"]]["name"]
    notify(username, "booking", f"Booked: {slot} at {place}",
           "Bring an ID. Eat and drink before you come. The centre does a short health check first "
           "and makes the final call.", place, ref=booking["id"], state=state)
    for staff, su in state["users"].items():
        if su["role"] == "centre" and su.get("org") == req["place"]:
            notify(staff, "booking", f"New booking: {name}, {slot}", f"{req['blood_type']} request {request_id}.",
                   "BloodSight", ref=booking["id"], state=state)
    save(state)
    return booking


def cancel_booking(username: str, booking_id: str) -> None:
    state = load()
    for b in state["bookings"]:
        if b["id"] == booking_id and b["username"] == username:
            b["status"] = "cancelled"
    save(state)


def decline(username: str, request_id: str) -> None:
    """'Not this time': costs nothing, stops the card, and is only ever counted."""
    state = load()
    if not any(d["request"] == request_id and d["username"] == username for d in state["declines"]):
        state["declines"].append({"request": request_id, "username": username})
    save(state)


def my_bookings(username: str) -> list[dict]:
    return [{**b, "place_name": PLACES[b["place"]]["name"]} for b in load()["bookings"]
            if b["username"] == username and b["status"] == "booked"]


def donations(username: str) -> dict:
    u = load()["users"][username]
    d = DONATIONS.get(u.get("lab_code"), {"total": 0, "places": 0, "history": []})
    return {**d, "history": [{**h, "place_name": PLACES[h["place"]]["name"]} for h in d["history"]]}


def reports_for(username: str) -> list[dict]:
    """Published reports, newest first. Nothing is shown unless the results switch is on."""
    state = load()
    u = state["users"][username]
    if not u["switches"].get("results"):
        return []
    published = BATCH_ID in state["lab"]["published_batches"]
    out = [r for r in REPORTS.get(u.get("lab_code"), []) if published or r["id"] not in BATCH_REPORT_IDS]
    return sorted(out, key=lambda r: r["date"], reverse=True)


def value_history(username: str, key: str) -> list[dict]:
    """One analyte across this person's published reports, oldest first."""
    out = []
    for r in reversed(reports_for(username)):
        v = next((v for v in r["values"] if v["key"] == key), None)
        if v:
            out.append({"date": r["date"], **v})
    return out


# -------------------------------------------------------------------- lab side

def batch() -> dict:
    """Today's batch from the lab system: totals, held-back reports, publish state."""
    state = load()["lab"]
    held = [{**h, "phoned": h["code"] in state["phoned"], "released": h["code"] in state["released"]}
            for h in BATCH_HELD]
    return {"id": BATCH_ID, **BATCH_TOTALS,
            "code_mismatch": sum(1 for h in held if h["reason"] == "mismatch" and not h["released"]),
            "urgent": sum(1 for h in held if h["reason"] == "urgent" and not h["released"]),
            "held": held, "published": BATCH_ID in state["published_batches"],
            "released_count": len(state["released"])}


def mark_phoned(code: str, by: str) -> None:
    """The doctor has phoned the patient: only now may an urgent value be released to the app."""
    state = load()
    if code not in state["lab"]["phoned"]:
        state["lab"]["phoned"].append(code)
    save(state)


def release_held(code: str) -> None:
    """Release a held report. Urgent ones need mark_phoned first; mismatches are released after a hand check."""
    state = load()
    h = next(x for x in BATCH_HELD if x["code"] == code)
    if h["reason"] == "urgent" and code not in state["lab"]["phoned"]:
        raise ValueError("Urgent values wait until the doctor has phoned.")
    if code not in state["lab"]["released"]:
        state["lab"]["released"].append(code)
    save(state)


def publish_batch(by: str) -> int:
    """Publish the ready reports. Every real account in the batch with the results switch on is notified,
    and the blood type is filled in from the result for patients who did not know it."""
    state = load()
    if BATCH_ID in state["lab"]["published_batches"]:
        return 0
    state["lab"]["published_batches"].append(BATCH_ID)
    for name, u in state["users"].items():
        if u["role"] != "patient":
            continue
        rep = next((r for r in REPORTS.get(u.get("lab_code"), []) if r["id"] in BATCH_REPORT_IDS), None)
        if not rep:
            continue
        if not u.get("blood_type"):
            u["blood_type"] = rep["blood_type"]
        if u["switches"].get("results"):
            out = [v for v in rep["values"] if v["flag"] != "In range"]
            notify(name, "results", f"Your blood test of {date.fromisoformat(rep['date']):%d %b} is ready".replace(" 0", " "),
                   f"{len(rep['values'])} values, {len(out)} out of range.", LAB_NAME, ref=rep["id"], state=state)
    save(state)
    return BATCH_TOTALS["ready"]
