"""Exercise actual HTTP serialization/error handling without using developer secrets."""
import json
from pathlib import Path

import httpx
import pytest
from streamlit.testing.v1 import AppTest

import data_store
import storage_config
import supabase_store as cloud

URL = "https://test-project.supabase.co"


@pytest.fixture
def cloud_env(monkeypatch):
    monkeypatch.setenv("BLOODSIGHT_DATA_BACKEND", "supabase")
    monkeypatch.setenv("SUPABASE_URL", URL)
    monkeypatch.setenv("SUPABASE_SECRET_KEY", "sb_secret_test_only")


def mock_http(monkeypatch, handler):
    client = httpx.Client
    monkeypatch.setattr(cloud.httpx, "Client", lambda **kwargs: client(transport=httpx.MockTransport(handler), **kwargs))


def test_history_pages_beyond_project_row_limit_and_scopes_owner(cloud_env, monkeypatch):
    offsets = []
    def handler(request):
        assert request.headers["apikey"] == "sb_secret_test_only"
        assert "authorization" not in request.headers
        assert request.url.params["place_id"] == "eq.rbc"
        assert request.url.params["order"] == "blood_type.asc,date.asc"
        offset = int(request.url.params["offset"])
        offsets.append(offset)
        # Simulate a project row cap smaller than the requested page size.
        dates = ["2026-01-01", "2026-01-02", "2026-01-03"][offset:offset+2]
        return httpx.Response(200, json=[dict(place_id="rbc", date=day, blood_type="O-",
            donations=10,demand=12,inventory=160,holiday=False,import_id="batch") for day in dates])
    mock_http(monkeypatch, handler)
    assert len(data_store.history_for("centre")) == 3
    assert offsets == [0, 2, 3]


def test_import_uses_validated_rows_and_trusted_account(cloud_env, monkeypatch, history_csv):
    calls = []
    def handler(request):
        calls.append(request)
        body = json.loads(request.content)
        assert request.url.path == "/rest/v1/rpc/bloodsight_import_history"
        assert body["p_owner"] == "rbc" and body["p_actor"] == "centre"
        assert body["p_filename"] == "history.csv"
        assert len(body["p_rows"]) == 70 and len(body["p_digest"]) == 64
        return httpx.Response(200, json={"id":"batch", "row_count":70, "duplicate":False})
    mock_http(monkeypatch, handler)
    assert data_store.import_history("centre", history_csv, "C:\\private\\history.csv")["row_count"] == 70
    with pytest.raises(ValueError, match="centre account"):
        data_store.import_history("patient", history_csv)
    with pytest.raises(ValueError):
        data_store.import_history("centre", b"not,a,valid,file")
    assert len(calls) == 1


def test_published_reports_are_scoped_and_measurements_sorted(cloud_env, monkeypatch):
    calls = []
    def handler(request):
        calls.append(request)
        assert request.url.params["lab_code"] == "eq.BL-4790"
        assert request.url.params["status"] == "eq.published"
        if request.url.params["offset"] != "0":
            return httpx.Response(200, json=[])
        return httpx.Response(200, json=[{"id":"IMP-1","date":"2026-09-21","lab":"Synthetic lab", "blood_type":"O-",
            "values":[{"key":"hb","line":2}, {"key":"ferritin","line":1}]}])
    mock_http(monkeypatch, handler)
    rows = cloud.published_reports_for("BL-4790")
    assert [v["key"] for v in rows[0]["values"]] == ["ferritin", "hb"]
    assert rows[0]["source"] == "Uploaded report"
    assert cloud.published_reports_for(None) == []
    assert len(calls) == 2


@pytest.mark.parametrize("status,body,message", [
    (403,{"message":"secret data"},"rejected access"),
    (404,{"message":"secret data"},"not ready"),
    (409,{"message":"secret data"},"already exists"),
    (400,{"code":"BS001","message":"secret data"},"phone call"),
    (400,{"code":"BS002","message":"secret data"},"not found"),
    (400,{"code":"BS003","message":"secret data"},"invalid"),
    (500,{"message":"secret data"},"could not complete"),
])
def test_provider_errors_do_not_expose_body_or_fallback(cloud_env, monkeypatch, status, body, message):
    mock_http(monkeypatch, lambda request: httpx.Response(status, json=body))
    with pytest.raises(storage_config.StorageUnavailable, match=message) as caught:
        data_store.history_for("centre")
    assert "secret data" not in str(caught.value)
    assert not data_store.db_path().exists()


def test_timeout_does_not_retry_a_mutation(cloud_env, monkeypatch, history_csv):
    calls = []
    def handler(request):
        calls.append(request)
        raise httpx.ReadTimeout("secret data", request=request)
    mock_http(monkeypatch, handler)
    with pytest.raises(storage_config.StorageUnavailable, match="timed out"):
        data_store.import_history("centre", history_csv)
    assert len(calls) == 1


@pytest.mark.parametrize("key", ["", "sb_publishable_test", "not-a-key"])
def test_missing_or_public_keys_fail_without_local_fallback(cloud_env, monkeypatch, key):
    monkeypatch.setenv("SUPABASE_SECRET_KEY", key)
    with pytest.raises(storage_config.StorageUnavailable, match="secret key"):
        data_store.history_for("centre")
    assert not data_store.db_path().exists()


def test_cloud_failure_is_readable_in_app(cloud_env, monkeypatch):
    monkeypatch.setenv("SUPABASE_SECRET_KEY", "")
    app = AppTest.from_file(str(Path(__file__).resolve().parents[1] / "app.py"), default_timeout=30)
    app.session_state["username"] = "centre"
    app.session_state["nav"] = "Data"
    app.run()
    assert not app.exception
    assert any("secret key" in e.value for e in app.error)
    assert not data_store.db_path().exists()


@pytest.mark.parametrize("url", ["http://test.supabase.co", "https://example.com", "https://test.supabase.co.evil.test",
    "https://test.supabase.co:invalid", "https://user:password@test.supabase.co", "https://test.supabase.co/rest/v1"])
def test_invalid_destinations_rejected_before_sending_key(cloud_env, monkeypatch, url):
    monkeypatch.setenv("SUPABASE_URL", url)
    def unexpected_request(request):
        pytest.fail("Invalid destinations must never receive the server key")
    mock_http(monkeypatch, unexpected_request)
    with pytest.raises(storage_config.StorageUnavailable, match="SUPABASE_URL"):
        cloud.check_connection()


def test_supabase_data_screen_can_save_manual_history(cloud_env, monkeypatch):
    saved = []
    def handler(request):
        if request.method == "POST":
            body = json.loads(request.content)
            saved.append(body)
            return httpx.Response(200, json={"id":"test", "row_count":1, "duplicate":False})
        return httpx.Response(200, json=[])
    mock_http(monkeypatch, handler)
    app = AppTest.from_file(str(Path(__file__).resolve().parents[1] / "app.py"), default_timeout=30)
    app.session_state["username"] = "centre"
    app.session_state["nav"] = "Data"
    app.run()
    assert not app.exception
    next(n for n in app.number_input if n.label == "Closing usable inventory (units)").set_value(432)
    next(b for b in app.button if b.label == "Save daily figures").click().run()
    assert not app.exception and len(saved) == 1
    assert saved[0]["p_owner"] == "rbc" and saved[0]["p_rows"][0]["inventory"] == 432
    assert any("Saved 1 records" in s.value for s in app.success)
