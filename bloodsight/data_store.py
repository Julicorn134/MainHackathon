"""Transactional storage for deposited data; demo accounts remain in store.py.

No upload is executable. Validate a whole batch before committing any rows.
SQL identifiers are fixed; values are bound parameters. Reads are role scoped.
"""
from __future__ import annotations

import csv
import hashlib
import io
import json
import math
import os
import re
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import date, datetime, timezone
from pathlib import Path

import pandas as pd

import store
import storage_config


def _cloud():
    if storage_config.settings()["backend"] == "supabase":
        import supabase_store
        return supabase_store
    return None

MAX_BYTES = 5 * 1024 * 1024
MAX_ROWS = 20000
HISTORY_COLUMNS = ["date", "blood_type", "donations", "demand", "inventory", "holiday"]


def db_path() -> Path:
    return Path(os.environ.get("BLOODSIGHT_DB") or store.STATE_PATH.with_suffix(".sqlite3"))


@contextmanager
def connection():
    path = db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(path, timeout=15)
    db.row_factory = sqlite3.Row
    try:
        db.execute("PRAGMA foreign_keys=ON")
        db.execute("PRAGMA journal_mode=WAL")
        db.executescript("""
            CREATE TABLE IF NOT EXISTS imports (
                id TEXT PRIMARY KEY, kind TEXT NOT NULL, owner TEXT NOT NULL,
                filename TEXT NOT NULL, digest TEXT NOT NULL, row_count INTEGER NOT NULL,
                created_by TEXT NOT NULL, created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS history (
                place_id TEXT NOT NULL, date TEXT NOT NULL, blood_type TEXT NOT NULL,
                donations INTEGER NOT NULL CHECK(donations>=0),
                demand INTEGER NOT NULL CHECK(demand>=0),
                inventory INTEGER NOT NULL CHECK(inventory>=0), holiday INTEGER NOT NULL,
                import_id TEXT NOT NULL REFERENCES imports(id),
                PRIMARY KEY(place_id, date, blood_type)
            );
            CREATE TABLE IF NOT EXISTS reports (
                id TEXT PRIMARY KEY, org TEXT NOT NULL, lab_code TEXT NOT NULL,
                date TEXT NOT NULL, payload TEXT NOT NULL, urgent INTEGER NOT NULL,
                status TEXT NOT NULL DEFAULT 'draft', phoned_by TEXT,
                published_at TEXT, import_id TEXT NOT NULL REFERENCES imports(id)
            );
        """)
        with db:
            yield db
    finally:
        db.close()


def _actor(username: str, role: str) -> dict:
    user = store.get_user(username)
    if not user or user["role"] != role:
        raise ValueError(f"This operation requires a {role} account.")
    return user


def _org(user: dict) -> str:
    org = user.get("org")
    if not org:
        raise ValueError("This account has no organisation.")
    return org


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _text(value, field: str, limit: int = 100) -> str:
    if not isinstance(value, str) or not value.strip() or len(value) > limit:
        raise ValueError(f"{field} must contain 1–{limit} characters.")
    # Imported labels are displayed in existing HTML cards: disallow markup.
    if any(c in value for c in ("<", ">", "\x00")):
        raise ValueError(f"{field} must be plain text without HTML.")
    return value.strip()


def _day(value, field="date") -> str:
    if not isinstance(value, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
        raise ValueError(f"{field} must use YYYY-MM-DD.")
    try:
        return date.fromisoformat(value).isoformat()
    except ValueError:
        raise ValueError(f"{field} is not a valid date.") from None


def _number(value, field: str, *, integer=False) -> float | int:
    if isinstance(value, bool):
        raise ValueError(f"{field} must be a number.")
    try:
        number = float(value)
    except (ValueError, TypeError):
        raise ValueError(f"{field} must be a number.") from None
    if not math.isfinite(number) or abs(number) > 10000000:
        raise ValueError(f"{field} must be finite and within 10 million.")
    if integer and (number < 0 or not number.is_integer()):
        raise ValueError(f"{field} must be a nonnegative whole number.")
    return int(number) if integer else number


def _boolean(value, field: str) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str) and value.strip().lower() in ("true", "false", "1", "0"):
        return value.strip().lower() in ("true", "1")
    raise ValueError(f"{field} must be true or false.")


def _decode(raw: bytes) -> str:
    if not raw or len(raw) > MAX_BYTES:
        raise ValueError("Upload a nonempty file no larger than 5 MB.")
    try:
        return raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        raise ValueError("Save the file as UTF-8 text.") from None


def parse_history(raw: bytes, place_id: str) -> list[dict]:
    reader = csv.DictReader(io.StringIO(_decode(raw)))
    fields = reader.fieldnames or []
    if len(set(fields)) != len(fields) or not set(HISTORY_COLUMNS).issubset(fields):
        raise ValueError("CSV columns required: " + ", ".join(HISTORY_COLUMNS))
    if set(fields) - set(HISTORY_COLUMNS + ["place_id"]):
        raise ValueError("Unexpected columns. Download the provided CSV template.")
    rows, seen = [], set()
    for i, row in enumerate(reader, start=2):
        if i > MAX_ROWS + 1:
            raise ValueError("A batch can contain at most 20,000 rows.")
        if None in row or any(v is None for v in row.values()):
            raise ValueError(f"Row {i}: inconsistent CSV column count.")
        if "place_id" in row and row["place_id"] != place_id:
            raise ValueError(f"Row {i}: facility must be your organisation ({place_id}).")
        try:
            item = {"date": _day(row["date"]), "blood_type": row["blood_type"].strip(),
                    **{k: _number(row[k], k, integer=True) for k in ("donations", "demand", "inventory")},
                    "holiday": _boolean(row["holiday"], "holiday")}
            if item["blood_type"] not in store.BLOOD_TYPES:
                raise ValueError("Unknown blood type.")
        except ValueError as exc:
            raise ValueError(f"Row {i}: {exc}") from None
        key = (item["date"], item["blood_type"])
        if key in seen:
            raise ValueError(f"Row {i}: duplicate date and blood type in this file.")
        seen.add(key)
        rows.append(item)
    if not rows:
        raise ValueError("The CSV has no data rows.")
    return sorted(rows, key=lambda r: (r["blood_type"], r["date"]))


def preview_history(username: str, raw: bytes) -> list[dict]:
    return parse_history(raw, _org(_actor(username, "centre")))


def _batch(db, kind, owner, rows, filename, username, *, deduplicate=True):
    digest = hashlib.sha256(json.dumps(rows, sort_keys=True, allow_nan=False).encode()).hexdigest()
    existing = db.execute("SELECT * FROM imports WHERE kind=? AND owner=? AND digest=?",
                          (kind, owner, digest)).fetchone()
    if existing and deduplicate:
        return dict(existing), True
    batch = dict(id=uuid.uuid4().hex, kind=kind, owner=owner,
                 filename=Path(filename.replace("\\", "/")).name[:160], digest=digest,
                 row_count=len(rows), created_by=username, created_at=_now())
    db.execute("INSERT INTO imports VALUES (:id,:kind,:owner,:filename,:digest,:row_count,:created_by,:created_at)", batch)
    return batch, False


def import_history(username: str, raw: bytes, filename: str = "manual-entry.csv") -> dict:
    place = _org(_actor(username, "centre"))
    rows = parse_history(raw, place)
    if cloud := _cloud():
        return cloud.import_history(place, username, rows, filename)
    with connection() as db:
        db.execute("BEGIN IMMEDIATE")
        current = {(r["date"], r["blood_type"]): dict(r) for r in db.execute(
            "SELECT * FROM history WHERE place_id=?", (place,))}
        unchanged = all(all(current.get((r["date"], r["blood_type"]), {}).get(k) == v
                            for k, v in r.items()) for r in rows)
        batch, duplicate = _batch(db, "history", place, rows, filename, username, deduplicate=unchanged)
        if not duplicate:
            db.executemany("""INSERT INTO history VALUES (?,?,?,?,?,?,?,?)
                ON CONFLICT(place_id,date,blood_type) DO UPDATE SET
                donations=excluded.donations, demand=excluded.demand,
                inventory=excluded.inventory, holiday=excluded.holiday, import_id=excluded.import_id""",
                [(place, r["date"], r["blood_type"], r["donations"], r["demand"], r["inventory"],
                  int(r["holiday"]), batch["id"]) for r in rows])
    return {**batch, "duplicate": duplicate}


def history_for(username: str) -> pd.DataFrame:
    place = _org(_actor(username, "centre"))
    if cloud := _cloud():
        return cloud.history_for(place)
    with connection() as db:
        df = pd.read_sql_query("SELECT * FROM history WHERE place_id=? ORDER BY blood_type,date", db, params=(place,))
    df["date"] = pd.to_datetime(df["date"])
    df["holiday"] = df["holiday"].astype(bool)
    return df


def imports_for(username: str) -> list[dict]:
    user = store.get_user(username)
    if not user or user["role"] not in ("centre", "lab"):
        raise ValueError("Import history is available to staff only.")
    kind = "history" if user["role"] == "centre" else "reports"
    if cloud := _cloud():
        return cloud.imports_for(_org(user), kind)
    with connection() as db:
        return [dict(r) for r in db.execute("SELECT * FROM imports WHERE kind=? AND owner=? ORDER BY created_at DESC",
                                          (kind, _org(user)))]


def parse_reports(raw: bytes) -> list[dict]:
    try:
        rows = json.loads(_decode(raw))
    except json.JSONDecodeError:
        raise ValueError("The file must be a JSON list of lab reports.") from None
    if not isinstance(rows, list) or not 1 <= len(rows) <= 200:
        raise ValueError("Upload a JSON list of 1–200 reports.")
    out, seen = [], set()
    for i, row in enumerate(rows, 1):
        if not isinstance(row, dict):
            raise ValueError(f"Report {i} must be an object.")
        required = {"lab_code", "date", "blood_type", "lab", "urgent", "values"}
        if set(row) != required:
            raise ValueError(f"Report {i} fields must be: {', '.join(sorted(required))}.")
        code = _text(row["lab_code"], "lab_code", 32)
        if not re.fullmatch(r"BL-[A-Z0-9-]{2,28}", code):
            raise ValueError("lab_code must look like BL-4821.")
        day = _day(row["date"])
        if (code, day) in seen:
            raise ValueError("Duplicate patient/date in the uploaded report batch.")
        seen.add((code, day))
        if row["blood_type"] not in store.BLOOD_TYPES:
            raise ValueError("Report blood type is not recognised.")
        values, keys = [], set()
        if not isinstance(row["values"], list) or not 1 <= len(row["values"]) <= 100:
            raise ValueError("Each report needs 1–100 measured values.")
        for line, v in enumerate(row["values"], 1):
            if not isinstance(v, dict) or set(v) != {"key", "name", "unit", "value", "low", "high"}:
                raise ValueError("Values require key, name, unit, value, low and high.")
            key = _text(v["key"], "value key", 40)
            if not re.fullmatch(r"[a-z][a-z0-9_]*", key) or key in keys:
                raise ValueError("Value keys must be unique lowercase identifiers.")
            keys.add(key)
            number, low, high = (_number(v[k], k) for k in ("value", "low", "high"))
            if low > high:
                raise ValueError("A reference range's lower bound exceeds its upper bound.")
            values.append(dict(key=key, name=_text(v["name"], "test name"), unit=_text(v["unit"], "unit", 40),
                               value=number, low=low, high=high, line=line,
                               flag="Low" if number < low else "High" if number > high else "In range"))
        out.append(dict(lab_code=code, date=day, blood_type=row["blood_type"], lab=_text(row["lab"], "lab"),
                        urgent=_boolean(row["urgent"], "urgent"), values=values))
    return out


def import_reports(username: str, raw: bytes, filename="reports.json") -> dict:
    org = _org(_actor(username, "lab"))
    rows = parse_reports(raw)
    if cloud := _cloud():
        return cloud.import_reports(org, username, rows, filename)
    with connection() as db:
        db.execute("BEGIN IMMEDIATE")
        batch, duplicate = _batch(db, "reports", org, rows, filename, username)
        if not duplicate:
            for r in rows:
                # Never silently overwrite a published measurement with an uploaded replacement.
                if db.execute("SELECT 1 FROM reports WHERE lab_code=? AND date=?", (r["lab_code"], r["date"])).fetchone():
                    raise ValueError(f"A deposited report already exists for {r['lab_code']} on {r['date']}; no reports were imported.")
                report_id = "IMP-" + uuid.uuid4().hex[:12]
                payload = {k: v for k, v in r.items() if k not in ("lab_code", "urgent")}
                payload.update(id=report_id, source="Uploaded report")
                db.execute("INSERT INTO reports(id,org,lab_code,date,payload,urgent,import_id) VALUES(?,?,?,?,?,?,?)",
                           (report_id, org, r["lab_code"], r["date"], json.dumps(payload), int(r["urgent"]), batch["id"]))
    return {**batch, "duplicate": duplicate}


def lab_reports(username: str) -> list[dict]:
    org = _org(_actor(username, "lab"))
    if cloud := _cloud():
        return cloud.lab_reports(org)
    with connection() as db:
        return [dict(r) for r in db.execute("SELECT id,lab_code,date,urgent,status,phoned_by,published_at FROM reports WHERE org=? ORDER BY date DESC", (org,))]


def publish_report(username: str, report_id: str, *, phone_call_recorded: bool = False) -> bool:
    org = _org(_actor(username, "lab"))
    if cloud := _cloud():
        return cloud.publish_report(org, username, report_id, phone_call_recorded)
    with connection() as db:
        db.execute("BEGIN IMMEDIATE")
        r = db.execute("SELECT * FROM reports WHERE id=? AND org=?", (report_id, org)).fetchone()
        if not r:
            raise ValueError("Report not found for this organisation.")
        if r["status"] == "published":
            return False
        if r["urgent"] and not (phone_call_recorded or r["phoned_by"]):
            raise ValueError("Record the doctor's phone call before publishing an urgent report.")
        db.execute("UPDATE reports SET status='published',published_at=?,phoned_by=? WHERE id=?",
                   (_now(), username if phone_call_recorded else r["phoned_by"], report_id))
    return True


def known_lab_codes() -> list[str]:
    if cloud := _cloud():
        return cloud.known_lab_codes()
    with connection() as db:
        return [r[0] for r in db.execute("SELECT DISTINCT lab_code FROM reports")]


def published_reports_for(username: str) -> list[dict]:
    user = _actor(username, "patient")
    if not user.get("switches", {}).get("results"):
        return []
    if cloud := _cloud():
        return cloud.published_reports_for(user.get("lab_code"))
    with connection() as db:
        return [json.loads(r[0]) for r in db.execute(
            "SELECT payload FROM reports WHERE lab_code=? AND status='published' ORDER BY date DESC,id",
            (user.get("lab_code"),))]
