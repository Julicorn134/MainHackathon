"""Supabase Data API adapter, called only after data_store checks identity and validates input.

The key stays on the Streamlit server. Database transactions live in RPC functions.
No automatic mutation retry: a lost response can be safely retried using batch deduplication.
"""
import hashlib
import json
from pathlib import Path

import httpx
import pandas as pd

from storage_config import StorageUnavailable, cloud_settings

PAGE_SIZE = 500
HISTORY_COLUMNS = ["place_id", "date", "blood_type", "donations", "demand", "inventory", "holiday", "import_id"]


def _request(method, path, *, params=None, body=None):
    config = cloud_settings()
    headers = {"apikey": config["key"], "Accept": "application/json"}
    if not config["key"].startswith("sb_secret_"):
        headers["Authorization"] = "Bearer " + config["key"]
    try:
        with httpx.Client(timeout=httpx.Timeout(45.0, connect=10.0), follow_redirects=False) as client:
            response = client.request(method, config["url"] + "/rest/v1/" + path,
                                      headers=headers, params=params, json=body)
        if response.status_code in (401, 403):
            raise StorageUnavailable("Supabase rejected access. Check the server's secret key and table permissions.")
        if response.status_code == 404:
            raise StorageUnavailable("BloodSight's Supabase tables are not ready. Apply the database migration first.")
        if response.status_code == 409:
            raise StorageUnavailable("A report already exists for a patient/date in this upload. No records were imported.")
        if not response.is_success:
            # Only allow known application codes; never surface raw SQL/provider messages.
            try:
                code = response.json().get("code")
            except (ValueError, AttributeError):
                code = None
            if code == "BS001":
                raise StorageUnavailable("Record the doctor's phone call before publishing an urgent report.")
            if code == "BS002":
                raise StorageUnavailable("Report not found for this organisation.")
            if code == "BS003":
                raise StorageUnavailable("This import is invalid. Check the template and try again; nothing was saved.")
            raise StorageUnavailable("Supabase could not complete this operation. Check the connection and database setup.")
        return response.json()
    except httpx.TimeoutException:
        raise StorageUnavailable("Supabase timed out. Refresh saved records before retrying; repeated imports are deduplicated.") from None
    except (httpx.HTTPError, ValueError) as exc:
        if isinstance(exc, StorageUnavailable):
            raise
        raise StorageUnavailable("Could not read a valid Supabase response. Check the connection and try again.") from None


def _rows(table, columns="*", **filters):
    """Page every query: Supabase's default row cap must not truncate a forecast."""
    result = []
    offset = 0
    while True:
        page = _request("GET", "bloodsight_" + table,
                        params={"select": columns, **filters, "limit": PAGE_SIZE, "offset": offset})
        if not isinstance(page, list):
            raise StorageUnavailable("Supabase returned an unexpected record format.")
        result.extend(page)
        # Continue to an empty page, including when a project sets a lower row cap.
        if not page:
            return result
        offset += len(page)


def check_connection():
    result = _request("POST", "rpc/bloodsight_storage_status", body={})
    if not isinstance(result, dict) or result.get("schema_version") != 1:
        raise StorageUnavailable("The Supabase schema does not match this version of BloodSight.")
    return result


def _import(kind, owner, username, rows, filename):
    digest = hashlib.sha256(json.dumps(rows, sort_keys=True, allow_nan=False).encode()).hexdigest()
    result = _request("POST", "rpc/bloodsight_import_" + kind, body={
        "p_owner": owner, "p_actor": username, "p_rows": rows,
        "p_filename": Path(filename.replace("\\", "/")).name[:160], "p_digest": digest})
    if not isinstance(result, dict) or not {"id", "row_count", "duplicate"}.issubset(result):
        raise StorageUnavailable("The import response was incomplete. Refresh saved records before retrying.")
    return result


def import_history(owner, username, rows, filename):
    return _import("history", owner, username, rows, filename)


def history_for(owner):
    rows = _rows("history", ",".join(HISTORY_COLUMNS), place_id="eq." + owner,
                 order="blood_type.asc,date.asc")
    df = pd.DataFrame(rows, columns=HISTORY_COLUMNS)
    df["date"] = pd.to_datetime(df["date"])
    df["holiday"] = df["holiday"].astype(bool)
    return df


def imports_for(owner, kind):
    return _rows("imports", owner="eq." + owner, kind="eq." + kind, order="created_at.desc,id.asc")


def import_reports(owner, username, rows, filename):
    return _import("reports", owner, username, rows, filename)


def lab_reports(owner):
    return _rows("reports", "id,lab_code,date,urgent,status,phoned_by,published_at",
                 org="eq." + owner, order="date.desc,id.asc")


def publish_report(owner, username, report_id, phone_call_recorded):
    result = _request("POST", "rpc/bloodsight_publish_report", body={
        "p_owner": owner, "p_actor": username, "p_report_id": report_id, "p_phoned": phone_call_recorded})
    if not isinstance(result, bool):
        raise StorageUnavailable("The publish response was incomplete. Refresh reports before retrying.")
    return result


def known_lab_codes():
    return sorted({r["lab_code"] for r in _rows("reports", "lab_code,id", order="id.asc")})


def published_reports_for(lab_code):
    if not lab_code:
        return []
    rows = _rows("reports", "id,date,lab,blood_type,values:bloodsight_report_values(key,name,unit,value,low,high,flag,line)",
                 lab_code="eq." + lab_code, status="eq.published", order="date.desc,id.asc")
    for row in rows:
        row["source"] = "Uploaded report"
        row["values"].sort(key=lambda v: v["line"])
    return rows
