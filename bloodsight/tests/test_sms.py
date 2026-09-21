import uuid
from pathlib import Path
from unittest.mock import Mock

import httpx
import pytest
from streamlit.testing.v1 import AppTest

import data_store
import sms_service as sms
import sms_store
import supabase_store
from storage_config import StorageUnavailable

PHONE = "+31600000000"  # Format fixture only; tests never contact Twilio.
SID = "SM" + "a" * 32


@pytest.fixture
def provider(monkeypatch):
    monkeypatch.setenv("TWILIO_ACCOUNT_SID", "AC" + "a" * 32)
    monkeypatch.setenv("TWILIO_AUTH_TOKEN", "test-token-not-a-secret")
    call = Mock(return_value=httpx.Response(201, json={"sid": SID, "status": "queued"}))
    monkeypatch.setattr(sms, "_request", call)
    return call


def saved(username="patient"):
    sms.save_contact(username, PHONE, True)
    return str(uuid.uuid4())


def test_save_normalizes_phone_without_sending(provider):
    sms.save_contact("patient", "+31 6-00000000", True)
    assert sms.contact_for("patient")["phone"] == PHONE
    assert not sms.contact_for("patient2")
    assert not provider.called


@pytest.mark.parametrize("phone", ["0612345678", "004912345678", "hello", "+31", "+31;test", "+0" + "1" * 10])
def test_invalid_phone_rejected(phone, provider):
    with pytest.raises(ValueError):
        sms.save_contact("patient", phone, True)
    assert not provider.called


def test_missing_or_revoked_consent_blocks_send(provider):
    for consent in (None, False, True):
        if consent is not None:
            sms.save_contact("patient", PHONE, consent)
        if consent is True:
            sms.save_contact("patient", PHONE, False)
        with pytest.raises(ValueError, match="agree"):
            sms.send_test("patient", str(uuid.uuid4()), PHONE)
    assert not provider.called


def test_changed_recipient_requires_new_preview(provider):
    attempt = saved()
    sms.save_contact("patient", "+31600000001", True)
    with pytest.raises(ValueError, match="Save your number"):
        sms.send_test("patient", attempt, PHONE)
    assert not provider.called


def test_trial_uses_template_once_and_delivery_is_not_claimed(provider):
    attempt = saved()
    first = sms.send_test("patient", attempt, PHONE)
    second = sms.send_test("patient", attempt, PHONE)
    assert provider.call_count == 1
    assert provider.call_args.args[3] == {"To": PHONE, "Body": sms.TRIAL_TEMPLATE}
    assert first["status"] == second["status"] == "queued"
    assert "not confirmed" in sms.status_text(first)


def test_custom_body_and_sender(provider, monkeypatch):
    monkeypatch.setenv("TWILIO_MESSAGE_MODE", "custom")
    attempt = saved()
    with pytest.raises(ValueError, match="sender"):
        sms.send_test("patient", attempt, PHONE)
    assert not sms.history_for("patient")
    monkeypatch.setenv("TWILIO_FROM_NUMBER", "+15005550006")
    sms.send_test("patient", attempt, PHONE)
    assert provider.call_args.args[3] == {"To": PHONE, "From": "+15005550006", "Body": sms.TEST_BODY}


def test_cooldown_and_shared_phone_limit(provider):
    sms.send_test("patient", saved(), PHONE)
    with pytest.raises(ValueError, match="limit"):
        sms.send_test("patient", str(uuid.uuid4()), PHONE)
    attempt2 = saved("patient2")
    with pytest.raises(ValueError, match="limit"):
        sms.send_test("patient2", attempt2, PHONE)
    assert provider.call_count == 1


def test_daily_cap(provider):
    for i in range(5):
        sms.send_test("patient", saved(), PHONE)
        with data_store.connection() as db:
            db.execute("UPDATE sms_attempts SET created_at=datetime('now','-2 minutes')")
    with pytest.raises(ValueError, match="limit"):
        sms.send_test("patient", str(uuid.uuid4()), PHONE)
    assert provider.call_count == 5


def test_uncertain_delivery_never_retried(provider):
    provider.side_effect = httpx.ReadTimeout("could contain sensitive transport details")
    attempt = saved()
    row = sms.send_test("patient", attempt, PHONE)
    assert row["status"] == "unknown"
    assert "uncertain" in sms.status_text(row)
    sms.send_test("patient", attempt, PHONE)
    assert provider.call_count == 1


def test_provider_rejection_is_sanitized(provider):
    provider.return_value = httpx.Response(400, json={"code": 21608, "message": "DO NOT DISPLAY SECRET"})
    row = sms.send_test("patient", saved(), PHONE)
    assert row["status"] == "failed" and row["error_code"] == "21608"
    assert "DO NOT DISPLAY" not in str(row) + sms.status_text(row)


def test_refresh_scoped_to_own_account_and_does_not_send(provider):
    attempt = saved()
    sms.send_test("patient", attempt, PHONE)
    with pytest.raises(ValueError, match="No trackable"):
        sms.refresh_delivery("patient2", attempt)
    assert not sms.history_for("patient2")
    provider.return_value = httpx.Response(200, json={"sid": SID, "status": "delivered"})
    assert sms.refresh_delivery("patient", attempt)["status"] == "delivered"
    assert provider.call_args.args[1] == "GET"
    provider.return_value = httpx.Response(200, json={"sid": SID, "status": "sent"})
    assert sms.refresh_delivery("patient", attempt)["status"] == "delivered"


def test_cloud_errors_do_not_send_or_fall_back(provider, monkeypatch):
    monkeypatch.setenv("BLOODSIGHT_DATA_BACKEND", "supabase")
    monkeypatch.setattr(supabase_store, "_request", Mock(side_effect=StorageUnavailable("Cloud unavailable")))
    with pytest.raises(StorageUnavailable):
        sms.send_test("patient", str(uuid.uuid4()), PHONE)
    assert not provider.called
    assert not data_store.db_path().exists()


def test_deleted_actor_cannot_use_saved_contact(provider):
    with pytest.raises(ValueError, match="Sign in"):
        sms.save_contact("nobody", PHONE, True)
    assert not provider.called


def test_ui_saves_phone_and_sends_only_on_click(provider):
    app = AppTest.from_file(str(Path(__file__).resolve().parents[1] / "app.py"), default_timeout=30)
    app.session_state["username"] = "patient"
    app.session_state["nav"] = "SMS test"
    app.run()
    assert not app.exception and not provider.called
    app.text_input[0].set_value(PHONE)
    app.checkbox[0].set_value(True)
    next(b for b in app.button if b.label == "Save phone number").click().run()
    assert not app.exception and not provider.called
    next(b for b in app.button if b.label == "Send test SMS").click().run()
    assert not app.exception and provider.call_count == 1
    app.run()
    assert provider.call_count == 1
    assert next(b for b in app.button if b.label == "Send test SMS").disabled


@pytest.mark.parametrize("username", ["centre", "lab", "patient2"])
def test_sms_screen_available_to_each_role(username, provider):
    app = AppTest.from_file(str(Path(__file__).resolve().parents[1] / "app.py"), default_timeout=30)
    app.session_state["username"] = username
    app.session_state["nav"] = "SMS test"
    app.run()
    assert not app.exception and not provider.called
