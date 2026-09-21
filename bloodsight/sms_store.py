"""Private SMS records. Selected cloud backend never falls back to offline storage.

The Streamlit server verifies the demo account before calling this adapter. This is
not production identity: deployment to real donors requires Supabase Auth first.
"""
from datetime import datetime, timedelta, timezone

import data_store
import storage_config


def _cloud():
    if storage_config.settings()["backend"] == "supabase":
        import supabase_store
        return supabase_store
    return None


def _tables(db):
    db.executescript("""
        CREATE TABLE IF NOT EXISTS sms_contacts (
            username TEXT PRIMARY KEY, phone TEXT NOT NULL, consent INTEGER NOT NULL,
            consent_at TEXT, updated_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS sms_attempts (
            id TEXT PRIMARY KEY, username TEXT NOT NULL, phone TEXT NOT NULL,
            body TEXT NOT NULL, mode TEXT NOT NULL, status TEXT NOT NULL,
            provider_sid TEXT, error_code TEXT, created_at TEXT NOT NULL, updated_at TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS sms_phone_date ON sms_attempts(phone,created_at);
        CREATE INDEX IF NOT EXISTS sms_user_date ON sms_attempts(username,created_at);
    """)


def contact_for(username):
    if cloud := _cloud():
        rows = cloud._rows("sms_contacts", username="eq." + username)
        return rows[0] if rows else None
    with data_store.connection() as db:
        _tables(db)
        row = db.execute("SELECT * FROM sms_contacts WHERE username=?", (username,)).fetchone()
        return dict(row) if row else None


def save_contact(username, phone, consent):
    if cloud := _cloud():
        return cloud._request("POST", "rpc/bloodsight_sms_contact", body={
            "p_actor": username, "p_phone": phone, "p_consent": consent})
    with data_store.connection() as db:
        _tables(db)
        now = data_store._now()
        db.execute("""INSERT INTO sms_contacts VALUES (?,?,?,?,?) ON CONFLICT(username) DO UPDATE SET
            phone=excluded.phone, consent=excluded.consent, consent_at=excluded.consent_at,
            updated_at=excluded.updated_at""", (username, phone, consent, now if consent else None, now))


def history_for(username):
    if cloud := _cloud():
        return cloud._request("GET", "bloodsight_sms_attempts", params={
            "username": "eq." + username, "order": "created_at.desc,id.desc", "limit": 20})
    with data_store.connection() as db:
        _tables(db)
        return [dict(r) for r in db.execute(
            "SELECT * FROM sms_attempts WHERE username=? ORDER BY created_at DESC,id DESC LIMIT 20", (username,))]


def reserve(username, attempt_id, phone, body, mode):
    if cloud := _cloud():
        return cloud._request("POST", "rpc/bloodsight_sms_reserve", body={
            "p_actor": username, "p_id": attempt_id, "p_phone": phone, "p_body": body, "p_mode": mode})
    with data_store.connection() as db:
        _tables(db)
        db.execute("BEGIN IMMEDIATE")
        existing = db.execute("SELECT * FROM sms_attempts WHERE id=?", (attempt_id,)).fetchone()
        if existing:
            if existing["username"] != username:
                raise ValueError("Prepare a new test for this account.")
            return {"send": False, "record": dict(existing)}
        contact = db.execute("SELECT * FROM sms_contacts WHERE username=?", (username,)).fetchone()
        if not contact or not contact["consent"] or contact["phone"] != phone:
            raise ValueError("Save your number and agree to receive test messages first.")
        now = datetime.now(timezone.utc)
        minute = (now - timedelta(seconds=60)).isoformat(timespec="seconds")
        day = (now - timedelta(hours=24)).isoformat(timespec="seconds")
        recent = db.execute("SELECT count(*) FROM sms_attempts WHERE (username=? OR phone=?) AND created_at>?",
                            (username, phone, minute)).fetchone()[0]
        daily = db.execute("SELECT count(*) FROM sms_attempts WHERE (username=? OR phone=?) AND created_at>?",
                           (username, phone, day)).fetchone()[0]
        total = db.execute("SELECT count(*) FROM sms_attempts WHERE created_at>?", (day,)).fetchone()[0]
        if recent or daily >= 5 or total >= 50:
            raise ValueError("Test limit reached: wait 60 seconds between attempts, with up to five per day per account/number.")
        stamp = now.isoformat(timespec="seconds")
        db.execute("INSERT INTO sms_attempts VALUES (?,?,?,?,?,?,?,?,?,?)",
                   (attempt_id, username, phone, body, mode, "submitting", None, None, stamp, stamp))
        row = db.execute("SELECT * FROM sms_attempts WHERE id=?", (attempt_id,)).fetchone()
        return {"send": True, "record": dict(row)}


def record(username, attempt_id, status, provider_sid, error_code):
    if cloud := _cloud():
        return cloud._request("POST", "rpc/bloodsight_sms_record", body={
            "p_actor": username, "p_id": attempt_id, "p_status": status,
            "p_sid": provider_sid, "p_error": error_code})
    with data_store.connection() as db:
        _tables(db)
        db.execute("""UPDATE sms_attempts SET status=?, provider_sid=coalesce(?,provider_sid),
                   error_code=?,updated_at=? WHERE id=? AND username=? AND status<>'delivered'""",
                   (status, provider_sid, error_code, data_store._now(), attempt_id, username))
        row = db.execute("SELECT * FROM sms_attempts WHERE id=? AND username=?", (attempt_id, username)).fetchone()
        if not row:
            raise ValueError("Message not found for this account.")
        return dict(row)
