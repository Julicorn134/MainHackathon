from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

import data_store

APP = Path(__file__).resolve().parents[1] / "app.py"


@pytest.mark.parametrize("username,page", [("centre", "Data"), ("centre", "Outlook"),
    ("centre", "AI assistant"), ("lab", "Data"), ("patient", "Results"),
    ("patient", "Ask"), ("patient2", "Ask")])
def test_new_and_existing_screens_render(username, page):
    app = AppTest.from_file(str(APP), default_timeout=30)
    app.session_state["username"] = username
    app.session_state["nav"] = page
    app.run()
    assert not app.exception


def test_uploaded_outlook_changes_after_saved_record(history_csv):
    data_store.import_history("centre", history_csv)
    app = AppTest.from_file(str(APP), default_timeout=30)
    app.session_state["username"] = "centre"
    app.session_state["nav"] = "Outlook"
    app.run()
    assert not app.exception
    assert app.metric[0].value == "160"
    data_store.import_history("centre", b"date,blood_type,donations,demand,inventory,holiday\n2026-03-11,O-,10,12,500,false\n")
    app.run()
    assert not app.exception
    assert app.metric[0].value == "500"
