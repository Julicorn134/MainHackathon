import copy
import io
import json
import os
from pathlib import Path
import subprocess
import sys

import pandas as pd
import pytest

import ai_service
import data_store as ds
import forecast
import forecast_data
import store


def test_history_persists_and_repeat_is_idempotent(history_csv):
    assert ds.history_for("centre").empty
    first = ds.import_history("centre", history_csv, "history.csv")
    assert first["row_count"] == 70
    assert ds.db_path().is_file()
    # Every reader opens a fresh connection: this is a disk read, not cached state.
    assert len(ds.history_for("centre")) == 70
    count = subprocess.check_output(
        [sys.executable, "-c", "import data_store; print(len(data_store.history_for('centre')))"],
        cwd=Path(__file__).resolve().parents[1],
        env={**os.environ, "BLOODSIGHT_STATE": str(store.STATE_PATH)}, text=True,
    )
    assert count.strip() == "70"
    assert ds.import_history("centre", history_csv)["duplicate"]
    assert len(ds.imports_for("centre")) == 1


def test_updated_rows_change_forecast_without_demo_fallback(history_csv):
    assert forecast_data.load("centre", "uploaded").empty
    ds.import_history("centre", history_csv)
    df = forecast_data.load("centre", "uploaded")
    before = forecast.forecast_type(df, "O-")
    update = pd.read_csv(io.BytesIO(history_csv)).tail(1)
    update["inventory"] = 500
    ds.import_history("centre", update.to_csv(index=False).encode())
    after = forecast.forecast_type(forecast_data.load("centre", "uploaded"), "O-")
    assert (after.raw - before.raw).round(4).tolist() == [340.0] * 14
    assert len(ds.history_for("centre")) == 70
    assert set(forecast.summary_table(df).blood_type) == {"O-"}


@pytest.mark.parametrize("field,value", [("donations", -1), ("demand", "nan"), ("inventory", "inf"),
                                          ("demand", 1.5), ("holiday", "maybe"), ("date", "01/02/2026"),
                                          ("blood_type", "Z-")])
def test_invalid_batch_is_rejected_atomically(history_csv, field, value):
    df = pd.read_csv(io.BytesIO(history_csv)).astype(object)
    df.loc[69, field] = value
    with pytest.raises(ValueError):
        ds.import_history("centre", df.to_csv(index=False).encode())
    assert ds.history_for("centre").empty
    assert ds.imports_for("centre") == []


def test_duplicate_keys_and_wrong_facility_rejected(history_csv):
    df = pd.read_csv(io.BytesIO(history_csv))
    with pytest.raises(ValueError, match="duplicate"):
        ds.import_history("centre", pd.concat([df, df.head(1)]).to_csv(index=False).encode())
    df["place_id"] = "mumc"
    with pytest.raises(ValueError, match="facility"):
        ds.import_history("centre", df.to_csv(index=False).encode())


def test_role_and_facility_scope(history_csv):
    with pytest.raises(ValueError):
        ds.import_history("patient", history_csv)
    with pytest.raises(ValueError):
        ds.history_for("lab")
    ds.import_history("centre", history_csv)
    state = store.load()
    state["users"]["centre2"] = {**state["users"]["centre"], "org": "mumc"}
    store.save(state)
    assert ds.history_for("centre2").empty
    assert ds.imports_for("centre2") == []
    packet = json.dumps(ai_service.evidence_for("centre"))
    for private_field in ("lab_code", "ferritin", "password_hash", "Alex Jansen"):
        assert private_field not in packet


def test_reimport_after_correction_restores_values(history_csv):
    ds.import_history("centre", history_csv)
    modified = pd.read_csv(io.BytesIO(history_csv)).tail(1)
    modified["inventory"] = 500
    ds.import_history("centre", modified.to_csv(index=False).encode())
    assert not ds.import_history("centre", history_csv)["duplicate"]
    assert ds.history_for("centre").inventory.iloc[-1] == 160
    assert len(ds.imports_for("centre")) == 3


def test_gaps_are_not_imputed_and_zero_demand_is_supported(history_csv):
    df = pd.read_csv(io.BytesIO(history_csv))
    ds.import_history("centre", df.drop(index=20).to_csv(index=False).encode())
    uploaded = forecast_data.load("centre", "uploaded")
    assert forecast_data.quality(uploaded)[0]["missing_days"] == 1
    assert forecast_data.ready_data(uploaded).empty
    df[["donations", "demand"]] = 0
    ds.import_history("centre", df.to_csv(index=False).encode())
    ready = forecast_data.ready_data(forecast_data.load("centre", "uploaded"))
    assert forecast.backtest(ready, "O-") == 0
    json.dumps(ai_service.evidence_for("centre"), allow_nan=False)


def test_lab_drafts_publication_isolation_and_real_values(report):
    original = store.reports_for("patient")
    batch = ds.import_reports("lab", json.dumps([report]).encode())
    assert not batch["duplicate"]
    assert store.reports_for("patient") == original
    rid = ds.lab_reports("lab")[0]["id"]
    assert ds.publish_report("lab", rid)
    assert not ds.publish_report("lab", rid)
    deposited = store.reports_for("patient")
    assert len(deposited) == 1
    assert deposited[0]["values"][0]["value"] == 33
    assert deposited[0]["source"] == "Uploaded report"
    assert all(r["id"] != rid for r in store.reports_for("patient2"))
    with pytest.raises(ValueError):
        ai_service.evidence_for("patient2", report_id=rid)
    store.update_user("patient", switches={"results": False})
    assert store.reports_for("patient") == []
    assert ds.import_reports("lab", json.dumps([report]).encode())["duplicate"]


def test_urgent_report_and_mutation_permissions(report):
    report["urgent"] = True
    ds.import_reports("lab", json.dumps([report]).encode())
    rid = ds.lab_reports("lab")[0]["id"]
    with pytest.raises(ValueError, match="phone"):
        ds.publish_report("lab", rid)
    with pytest.raises(ValueError):
        ds.publish_report("patient", rid, phone_call_recorded=True)
    assert ds.publish_report("lab", rid, phone_call_recorded=True)


def test_lab_conflict_rolls_back_whole_new_batch(report):
    ds.import_reports("lab", json.dumps([report]).encode())
    new = copy.deepcopy(report)
    new["date"] = "2026-09-22"
    changed = copy.deepcopy(report)
    changed["values"][0]["value"] = 99
    with pytest.raises(ValueError, match="already exists"):
        ds.import_reports("lab", json.dumps([new, changed]).encode())
    assert len(ds.lab_reports("lab")) == 1
    assert len(ds.imports_for("lab")) == 1


@pytest.mark.parametrize("patch", [{"value": "NaN"}, {"low": 900}, {"name": "<script>bad</script>"}])
def test_report_validation(report, patch):
    report["values"][0].update(patch)
    with pytest.raises(ValueError):
        ds.import_reports("lab", json.dumps([report]).encode())
    assert ds.lab_reports("lab") == []


def test_new_deposited_lab_code_can_register(report):
    report["lab_code"] = "BL-9001"
    ds.import_reports("lab", json.dumps([report]).encode())
    assert "BL-9001" in store.unclaimed_lab_codes()
    user = store.register_patient("BL-9001", "newdonor", "testpassword", "Test Person", "0000", None,
                                  {"results": True, "nearby": False, "gave_before": False})
    assert user["username"] == "newdonor"
    assert store.reports_for("newdonor") == []
