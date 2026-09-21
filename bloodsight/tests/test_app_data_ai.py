import json
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

import data_store
import store

APP = Path(__file__).resolve().parents[1] / "app.py"


@pytest.mark.parametrize("username,page", [("centre", "Data"), ("centre", "Outlook"),
    ("centre", "AI assistant"), ("lab", "Data"), ("patient", "Results"),
    ("patient", "Ask"), ("patient2", "Ask"),
    ("centre", "Requests"), ("centre", "Bookings"), ("centre", "Network"),
    ("centre", "Hospital orders"), ("centre", "Notifications"),
    ("hospital", "Data"), ("hospital", "Outlook"), ("hospital", "Hospital orders"),
    ("lab", "Publish results"), ("lab", "Patients"), ("lab", "Blood requests"),
    ("lab", "Notify patients"), ("lab", "Donor link"), ("lab", "Notifications"),
    ("patient", "Needs"), ("patient", "Donations"), ("patient", "Me")])
def test_new_and_existing_screens_render(username, page):
    app = AppTest.from_file(str(APP), default_timeout=30)
    app.session_state["username"] = username
    app.session_state["nav"] = page
    app.run()
    assert not app.exception
    assert app.session_state["nav"] == page


def test_uploaded_outlook_changes_after_saved_record(history_csv):
    data_store.import_history("centre", history_csv)
    app = AppTest.from_file(str(APP), default_timeout=30)
    app.session_state["username"] = "centre"
    app.session_state["nav"] = "Outlook"
    app.run()
    assert not app.exception
    assert any('Units in stock</div><div class="v">160</div>' in m.value for m in app.markdown)
    data_store.import_history("centre", b"date,blood_type,donations,demand,inventory,holiday\n2026-03-11,O-,10,12,500,false\n")
    app.run()
    assert not app.exception
    assert any('Units in stock</div><div class="v">500</div>' in m.value for m in app.markdown)


def test_sign_up_without_lab_code_then_link_imported_report(report):
    # The redesigned sign-up flow must still reach uploaded reports, including
    # after the separate bundled batch was published.
    store.publish_batch("lab")
    app = AppTest.from_file(str(APP), default_timeout=30).run()
    assert not app.exception
    for label, value in [("Your name", "Synthetic Donor"), ("Choose a username", "newdonor"),
                         ("Choose a password", "testing123"), ("Where do you live?", "6211")]:
        next(t for t in app.text_input if t.label == label).set_value(value)
    next(b for b in app.button if b.label == "Continue").click().run()
    assert not app.exception
    assert store.get_user("newdonor")["lab_code"] is None

    report["lab_code"] = "BL-NEW-UPLOAD"
    data_store.import_reports("lab", json.dumps([report]).encode())
    data_store.publish_report("lab", data_store.lab_reports("lab")[0]["id"])
    next(t for t in app.text_input if t.label == "Lab code").set_value(report["lab_code"])
    next(b for b in app.button if b.label == "Link").click().run()
    assert not app.exception
    assert store.get_user("newdonor")["lab_code"] == report["lab_code"]
    assert store.reports_for("newdonor")[0]["values"][0]["value"] == 33
    assert any("Uploaded report" in c.value for c in app.caption)


def test_register_with_imported_code_after_publishing_bundled_batch(report):
    store.publish_batch("lab")
    report["lab_code"] = "BL-NEW-UPLOAD"
    data_store.import_reports("lab", json.dumps([report]).encode())
    user = store.register_patient(report["lab_code"], "newdonor", "testing123", "Synthetic", "6211", None, {})
    assert user["lab_code"] == report["lab_code"]


def test_hospital_outlook_does_not_show_another_centres_history(history_csv):
    data_store.import_history("centre", history_csv)
    app = AppTest.from_file(str(APP), default_timeout=30)
    app.session_state["username"] = "hospital"
    app.session_state["nav"] = "Outlook"
    app.run()
    assert not app.exception and not app.metric
    assert any("No forecast-ready records" in i.value for i in app.info)
