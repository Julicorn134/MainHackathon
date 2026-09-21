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
        st.info("This exact batch was already saved. No duplicate records were created.")
    else:
        st.success(f"Saved {result['row_count']} records. They remain available after restarting the app.")


def _history(user):
    name = user["username"]
    st.caption(f"Facility: {store.PLACES.get(user['org'], {}).get('name', user['org'])}. "
               "Record daily donations, demand and closing usable inventory in units. Use synthetic test data for this prototype.")
    sample = forecast.load_data().to_csv(index=False).encode("utf-8")
    st.download_button("Download sample history CSV", sample, "bloodsight-history.csv", "text/csv")
    st.caption("The sample is labelled synthetic. Files may contain one or more blood types. "
               "Forecasts need at least 42 consecutive daily records per type; missing days are not treated as zero.")
    upload = st.file_uploader("Upload daily history (CSV, up to 5 MB)", type=["csv"], key="history_upload")
    if upload:
        try:
            rows = data_store.preview_history(name, upload.getvalue())
            st.dataframe(pd.DataFrame(rows).head(50), hide_index=True)
            st.caption(f"{len(rows)} validated rows. Same date/type replaces the earlier stored row; other dates remain. "
                       "An unchanged repeat is ignored. Reimporting after a correction applies the uploaded values again.")
            if st.button("Save history", type="primary"):
                _saved(data_store.import_history(name, upload.getvalue(), upload.name))
        except ValueError as exc:
            st.error(str(exc))

    with st.expander("Enter one day's figures"):
        with st.form("daily_history"):
            day = st.date_input("Date", value=store.today())
            bt = st.selectbox("Blood type", store.BLOOD_TYPES)
            a, b, c = st.columns(3)
            donations = a.number_input("Donations received (units)", min_value=0, max_value=10000000, step=1)
            demand = b.number_input("Demand (units)", min_value=0, max_value=10000000, step=1)
            inventory = c.number_input("Closing usable inventory (units)", min_value=0, max_value=10000000, step=1)
            holiday = st.checkbox("Local holiday")
            submit = st.form_submit_button("Save daily figures")
        if submit:
            row = dict(date=day.isoformat(), blood_type=bt, donations=donations, demand=demand,
                       inventory=inventory, holiday=holiday)
            raw = pd.DataFrame([row]).to_csv(index=False).encode()
            try:
                _saved(data_store.import_history(name, raw))
            except ValueError as exc:
                st.error(str(exc))

    history = data_store.history_for(name)
    st.subheader("Saved history")
    if history.empty:
        st.info("No uploaded history yet. Save a CSV or daily figures above, then select Uploaded data in Outlook.")
    else:
        st.dataframe(pd.DataFrame(forecast_data.quality(history)), hide_index=True)
        st.dataframe(history.drop(columns=["import_id"]).tail(100), hide_index=True)
        exported = history.drop(columns=["import_id"]).to_csv(index=False).encode()
        st.download_button("Export saved history", exported, "saved-history.csv", "text/csv")


def _reports(user):
    name = user["username"]
    st.caption("Import synthetic lab reports or enter a measured value. Records are saved as drafts. "
               "Review them before publishing to the matching lab-code account.")
    sample = [{"lab_code": "BL-4790", "date": "2026-09-21", "blood_type": "O-",
               "lab": "Synthetic test laboratory", "urgent": False,
               "values": [{"key": "ferritin", "name": "Ferritin", "unit": "ng/mL",
                           "value": 33, "low": 30, "high": 300}]}]
    st.download_button("Download report JSON template", json.dumps(sample, indent=2), "lab-reports.json", "application/json")
    upload = st.file_uploader("Upload lab reports (JSON, up to 5 MB)", type=["json"], key="reports_upload")
    if upload:
        try:
            rows = data_store.parse_reports(upload.getvalue())
            st.dataframe([{k: r[k] for k in ("lab_code", "date", "blood_type", "lab", "urgent")}
                          for r in rows], hide_index=True)
            with st.expander("Review measured values"):
                st.json(rows)
            if st.button("Save report drafts", type="primary"):
                _saved(data_store.import_reports(name, upload.getvalue(), upload.name))
        except ValueError as exc:
            st.error(str(exc))

    with st.expander("Enter a report with one measured value"):
        st.caption("For multiple measured values in one report, use the JSON template. "
                   "Existing patient/date reports cannot be silently replaced.")
        with st.form("manual_report"):
            code = st.text_input("Lab code", value="BL-4790")
            day = st.date_input("Report date", value=store.today())
            bt = st.selectbox("Reported blood type", store.BLOOD_TYPES)
            a, b = st.columns(2)
            key = a.text_input("Test identifier", value="ferritin", help="Lowercase, e.g. ferritin or hb.")
            label = b.text_input("Test name", value="Ferritin")
            unit = st.text_input("Unit", value="ng/mL")
            a, b, c = st.columns(3)
            value = a.number_input("Measured value", value=33.0)
            low = b.number_input("Lab range: lower", value=30.0)
            high = c.number_input("Lab range: upper", value=300.0)
            urgent = st.checkbox("Flagged urgent by the lab")
            submit = st.form_submit_button("Save draft report")
        if submit:
            report = dict(lab_code=code, date=day.isoformat(), blood_type=bt, lab=store.LAB_NAME,
                          urgent=urgent, values=[dict(key=key, name=label, unit=unit, value=value, low=low, high=high)])
            try:
                _saved(data_store.import_reports(name, json.dumps([report]).encode(), "manual-report.json"))
            except ValueError as exc:
                st.error(str(exc))

    st.subheader("Saved reports")
    reports = data_store.lab_reports(name)
    if not reports:
        st.info("No reports deposited yet.")
        return
    st.dataframe(reports, hide_index=True)
    drafts = [r for r in reports if r["status"] == "draft"]
    if drafts:
        selected = st.selectbox("Draft to publish", [r["id"] for r in drafts],
                                format_func=lambda rid: next(f"{r['lab_code']} · {r['date']} · {rid}" for r in drafts if r["id"] == rid))
        phoned = st.checkbox("The doctor has phoned (required for urgent reports)", key=f"called_{selected}")
        if st.button("Publish selected report"):
            try:
                data_store.publish_report(name, selected, phone_call_recorded=phoned)
                st.success("Published. It is now available in the matching patient's Results and AI context.")
            except ValueError as exc:
                st.error(str(exc))


def render(user):
    fresh = store.get_user(user["username"])
    if not fresh or fresh["role"] not in ("centre", "lab"):
        st.error("Only staff can deposit data.")
        return
    ui.header("Data", "Save, review and reuse your team's test records.")
    config = storage_config.settings()
    if config["backend"] == "supabase":
        st.caption("Storage destination: Supabase · " + config["url"])
        if st.button("Check database connection"):
            try:
                import supabase_store
                supabase_store.check_connection()
                st.success("Connected. BloodSight's tables are ready to receive uploads.")
            except storage_config.StorageUnavailable as exc:
                st.error(str(exc))
    else:
        st.caption("Storage destination: local test database on this app server.")
    if fresh["role"] == "centre":
        _history(fresh)
    else:
        _reports(fresh)
    with st.expander("Import history"):
        logs = data_store.imports_for(fresh["username"])
        st.dataframe([{k: r[k] for k in ("filename", "row_count", "created_at", "created_by")}
                      for r in logs], hide_index=True) if logs else st.caption("No imports yet.")
