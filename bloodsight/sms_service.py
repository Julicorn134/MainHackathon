"""Explicit, single-recipient SMS tests. No sends from forecasts or page rendering."""
import os
import re
import uuid

import httpx

import ai_config
import sms_store
import store

TEST_BODY = ("BloodSight DEMO: A simulated blood shortage is forecast. This is a test donation "
             "request for our hackathon, not a real emergency.")
TRIAL_TEMPLATE = "sms_account_alerts"
STATUSES = {"accepted", "queued", "sending", "sent", "delivered", "undelivered", "failed", "canceled"}


class SmsError(ValueError):
    """Safe to show; never contains credentials or a raw provider response."""


def actor(username):
    user = store.get_user(username)
    if not user or user.get("role") not in ("patient", "centre", "lab"):
        raise SmsError("Sign in before using SMS.")
    return user


def normalize_phone(value):
    # Do not guess a country from the server's location or silently drop a trunk zero.
    phone = re.sub(r"[\s()\-]", "", str(value))
    if not re.fullmatch(r"\+[1-9][0-9]{7,14}", phone):
        raise SmsError("Use your mobile number with its country code, for example +31 or +49.")
    return phone


def settings():
    local = ai_config.read_secrets()
    def get(key, default=""):
        return str(os.environ.get(key) or local.get(key) or default).strip()
    config = {"sid": get("TWILIO_ACCOUNT_SID"), "token": get("TWILIO_AUTH_TOKEN"),
              "sender": get("TWILIO_FROM_NUMBER"), "service": get("TWILIO_MESSAGING_SERVICE_SID"),
              "mode": get("TWILIO_MESSAGE_MODE", "trial_template")}
    if config["mode"] not in ("trial_template", "custom"):
        raise SmsError("Choose trial_template or custom for TWILIO_MESSAGE_MODE in private settings.")
    return config


def ready_config():
    c = settings()
    if not re.fullmatch(r"AC[0-9a-fA-F]{32}", c["sid"]) or not c["token"]:
        raise SmsError("Add the Twilio account SID and auth token in private server settings.")
    if c["mode"] == "custom":
        if c["service"]:
            if not re.fullmatch(r"MG[0-9a-fA-F]{32}", c["service"]):
                raise SmsError("Check the Twilio Messaging Service SID in private settings.")
        elif not re.fullmatch(r"\+[1-9][0-9]{7,14}", c["sender"]):
            raise SmsError("Configure an SMS-capable Twilio sender in private settings first.")
    return c


def contact_for(username):
    actor(username)
    return sms_store.contact_for(username)


def save_contact(username, phone, consent):
    actor(username)
    if not isinstance(consent, bool):
        raise SmsError("Confirm whether you want to receive test messages.")
    phone = normalize_phone(phone) if str(phone).strip() else ""
    if consent and not phone:
        raise SmsError("Enter your own mobile number before enabling SMS.")
    sms_store.save_contact(username, phone, consent)


def history_for(username):
    actor(username)
    return sms_store.history_for(username)


def _request(config, method, path, data=None):
    url = f"https://api.twilio.com/2010-04-01/Accounts/{config['sid']}/{path}"
    # Fixed endpoint; credentials must never follow a redirect. No automatic POST retry.
    with httpx.Client(timeout=httpx.Timeout(20, connect=8), follow_redirects=False) as client:
        return client.request(method, url, auth=(config["sid"], config["token"]), data=data)


def _payload(response):
    try:
        data = response.json()
        return data if isinstance(data, dict) else {}
    except ValueError:
        return {}


def _error_code(data):
    code = str(data.get("error_code") or data.get("code") or "")
    return code if re.fullmatch(r"[0-9]{3,6}", code) else None


def send_test(username, attempt_id, expected_phone):
    actor(username)
    config = ready_config()
    try:
        attempt_id = str(uuid.UUID(str(attempt_id)))
    except ValueError:
        raise SmsError("Prepare a new test before sending.") from None
    expected_phone = normalize_phone(expected_phone)
    body = TRIAL_TEMPLATE if config["mode"] == "trial_template" else TEST_BODY
    reserved = sms_store.reserve(username, attempt_id, expected_phone, body, config["mode"])
    row = reserved["record"]
    if not reserved["send"]:
        return row
    data = {"To": row["phone"], "Body": body}
    if config["mode"] == "custom":
        if config["service"]:
            data["MessagingServiceSid"] = config["service"]
        else:
            data["From"] = config["sender"]
    # The current Twilio trial API assigns the sender and only accepts To/Body (+ callback).
    # Its Body is a provider template identifier, never the custom BloodSight wording.
    status, sid, error = "unknown", None, None
    try:
        response = _request(config, "POST", "Messages.json", data)
        payload = _payload(response)
        error = _error_code(payload)
        candidate = payload.get("sid", "")
        if response.is_success and isinstance(candidate, str) and re.fullmatch(r"SM[0-9a-fA-F]{32}", candidate):
            sid = candidate
            status = payload.get("status") if payload.get("status") in STATUSES else "accepted"
        elif 400 <= response.status_code < 500:
            status = "failed"
    except httpx.HTTPError:
        # A timeout can occur AFTER Twilio accepted the message. Do not resend this attempt.
        pass
    return sms_store.record(username, attempt_id, status, sid, error)


def refresh_delivery(username, attempt_id):
    actor(username)
    row = next((r for r in history_for(username) if r["id"] == attempt_id), None)
    if not row or not row.get("provider_sid"):
        raise SmsError("No trackable message was found for this account.")
    try:
        response = _request(ready_config(), "GET", f"Messages/{row['provider_sid']}.json")
        payload = _payload(response)
    except httpx.HTTPError:
        raise SmsError("Could not check delivery. The message has not been sent again.") from None
    if not response.is_success or payload.get("sid") != row["provider_sid"] or payload.get("status") not in STATUSES:
        raise SmsError("Twilio could not confirm delivery status. Check its message log.")
    return sms_store.record(username, attempt_id, payload["status"], row["provider_sid"], _error_code(payload))


def status_text(row):
    state = row["status"]
    if state == "delivered":
        return "Twilio reports delivery to the destination."
    if state in ("unknown", "submitting"):
        return "Delivery is uncertain. Check Twilio's message log before preparing another test."
    if state in ("failed", "undelivered", "canceled"):
        code = row.get("error_code")
        suffix = f" Reference: {code}." if code else ""
        return "Not delivered. Check recipient verification, country permissions and sender setup in Twilio." + suffix
    if state == "sent":
        return "The carrier accepted the SMS. Delivery is not confirmed yet."
    return "Twilio accepted the message. Delivery is not confirmed yet."
