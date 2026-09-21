"""Deposit and review data through the application, without editing source files."""
import json

import pandas as pd
import streamlit as st

import data_store
import forecast_data
import forecast
import store
import storage_config
import ui


def _saved(result):
    if result["duplicate"]:
        st.info("Already saved. No duplicates added.")
    else:
        st.success(f"Saved {result['row_count']} records.")


def _history(user):
    name = user["username"]
    ui.section("Daily inventory")
    st.caption("Donations, demand and closing stock in units. Forecasts need 42 consecutive days per blood type.")
    sample = forecast.load_data().to_csv(index=False).encode("utf-8")
    upload_tab, entry_tab = st.tabs(["Upload CSV", "Daily entry"])
    with upload_tab:
        upload = st.file_uploader("Daily history", type=["csv"], key="history_upload",
                                  help="CSV, up to 5 MB. Corrections replace records with the same date and blood type.")
        st.download_button("Download sample history CSV", sample, "bloodsight-history.csv", "text/csv")
        st.caption("Download contains synthetic sample records.")
        if upload:
            try:
                rows = data_store.preview_history(name, upload.getvalue())
                st.dataframe(pd.DataFrame(rows).head(50), hide_index=True)
                st.caption(f"{len(rows)} validated rows. Matching dates and blood types will be updated.")
                if st.button("Save history", type="primary"):
                    _saved(data_store.import_history(name, upload.getvalue(), upload.name))
            except ValueError as exc:
                st.error(str(exc))
    with entry_tab:
        with st.form("daily_history", border=False):
            a, b = st.columns(2)
            day = a.date_input("Date", value=store.today())
            bt = b.selectbox("Blood type", store.BLOOD_TYPES)
            a, b, c = st.columns(3)
            donations = a.number_input("Donations received (units)", min_value=0, max_value=10000000, step=1)
            demand = b.number_input("Demand (units)", min_value=0, max_value=10000000, step=1)
            inventory = c.number_input("Closing usable inventory (units)", min_value=0, max_value=10000000, step=1)
            holiday = st.checkbox("Local holiday")
            submit = st.form_submit_button("Save daily figures", type="primary")
        if submit:
            row = dict(date=day.isoformat(), blood_type=bt, donations=donations, demand=demand,
                       inventory=inventory, holiday=holiday)
            raw = pd.DataFrame([row]).to_csv(index=False).encode()
            try:
                _saved(data_store.import_history(name, raw))
            except ValueError as exc:
                st.error(str(exc))

    history = data_store.history_for(name)
    ui.section("Saved history")
    if history.empty:
        st.info("No uploaded history yet. Save a CSV or daily figures above, then select Saved records in Outlook.")
    else:
        st.dataframe(pd.DataFrame(forecast_data.quality(history)), hide_index=True)
        st.dataframe(history.drop(columns=["import_id"]).tail(100), hide_index=True)
        exported = history.drop(columns=["import_id"]).to_csv(index=False).encode()
        st.download_button("Export saved history", exported, "saved-history.csv", "text/csv")


def _reports(user):
    name = user["username"]
    ui.section("Lab reports")
    st.caption("Imports are saved as drafts for review before publication.")
    sample = [{"lab_code": "BL-4790", "date": "2026-09-21", "blood_type": "O-",
               "lab": "Synthetic test laboratory", "urgent": False,
               "values": [{"key": "ferritin", "name": "Ferritin", "unit": "ng/mL",
                           "value": 33, "low": 30, "high": 300}]}]
    upload_tab, entry_tab = st.tabs(["Upload JSON", "Manual entry"])
    with upload_tab:
        upload = st.file_uploader("Lab reports", type=["json"], key="reports_upload", help="JSON, up to 5 MB.")
        st.download_button("Download report JSON template", json.dumps(sample, indent=2), "lab-reports.json", "application/json")
        st.caption("Template contains a synthetic example report.")
        if upload:
            try:
                rows = data_store.parse_reports(upload.getvalue())
                st.dataframe([{k: r[k] for k in ("lab_code", "date", "blood_type", "lab", "urgent")}
                              for r in rows], hide_index=True)
                ui.section("Measured values")
                st.dataframe([{"Lab code": r["lab_code"], "Date": r["date"], **v}
                              for r in rows for v in r["values"]], hide_index=True)
                if st.button("Save report drafts", type="primary"):
                    _saved(data_store.import_reports(name, upload.getvalue(), upload.name))
            except ValueError as exc:
                st.error(str(exc))
    with entry_tab:
        st.caption("One measured value per entry. For a full panel, use the JSON template.")
        with st.form("manual_report", border=False):
            a, b, c = st.columns(3)
            code = a.text_input("Lab code", value="BL-4790")
            day = b.date_input("Report date", value=store.today())
            bt = c.selectbox("Reported blood type", store.BLOOD_TYPES)
            a, b = st.columns(2)
            key = a.text_input("Test identifier", value="ferritin", help="Lowercase, e.g. ferritin or hb.")
            label = b.text_input("Test name", value="Ferritin")
            unit = st.text_input("Unit", value="ng/mL")
            a, b, c = st.columns(3)
            value = a.number_input("Measured value", value=33.0)
            low = b.number_input("Lab range: lower", value=30.0)
            high = c.number_input("Lab range: upper", value=300.0)
            urgent = st.checkbox("Flagged urgent by the lab")
            submit = st.form_submit_button("Save draft report", type="primary")
        if submit:
            report = dict(lab_code=code, date=day.isoformat(), blood_type=bt, lab=store.LAB_NAME,
                          urgent=urgent, values=[dict(key=key, name=label, unit=unit, value=value, low=low, high=high)])
            try:
                _saved(data_store.import_reports(name, json.dumps([report]).encode(), "manual-report.json"))
            except ValueError as exc:
                st.error(str(exc))

    ui.section("Saved reports")
    reports = data_store.lab_reports(name)
    if not reports:
        st.info("No reports deposited yet.")
        return
    st.dataframe(reports, hide_index=True)
    drafts = [r for r in reports if r["status"] == "draft"]
    if drafts:
        selected = st.selectbox("Draft to publish", [r["id"] for r in drafts],
                                format_func=lambda rid: next(f"{r['lab_code']} · {r['date']}" for r in drafts if r["id"] == rid))
        phoned = st.checkbox("The doctor has phoned (required for urgent reports)", key=f"called_{selected}")
        if st.button("Publish selected report"):
            try:
                data_store.publish_report(name, selected, phone_call_recorded=phoned)
                st.success("Report published.")
            except ValueError as exc:
                st.error(str(exc))


def render(user):
    fresh = store.get_user(user["username"])
    if not fresh or fresh["role"] not in ("centre", "lab"):
        st.error("Only staff can deposit data.")
        return
    ui.header("Data", "Imports and saved records")
    config = storage_config.settings()
    if config["backend"] == "supabase":
        st.caption("Shared database · Supabase")
        if st.button("Check database connection"):
            try:
                import supabase_store
                supabase_store.check_connection()
                st.success("Database connected.")
            except storage_config.StorageUnavailable as exc:
                st.error(str(exc))
    else:
        st.caption("Local test database")
    if fresh["role"] == "centre":
        _history(fresh)
    else:
        _reports(fresh)
    ui.section("Import history")
    logs = data_store.imports_for(fresh["username"])
    st.dataframe([{k: r[k] for k in ("filename", "row_count", "created_at", "created_by")}
                  for r in logs], hide_index=True) if logs else st.caption("No imports yet.")
