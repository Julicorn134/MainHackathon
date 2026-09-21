"""One saved phone, explicit test submission, persistent delivery history."""
import uuid

import streamlit as st

import sms_service as sms
import ui


def render(user):
    ui.header("SMS test", "Send a test message to your own phone.")
    username = user["username"]
    contact = sms.contact_for(username) or {}
    flash = st.session_state.pop("sms_flash", None)
    if flash:
        st.success(flash)
    with st.form("sms_contact"):
        phone = st.text_input("Your mobile number", value=contact.get("phone", ""),
                              placeholder="Country code followed by your number", max_chars=32)
        consent = st.checkbox("This is my number and I agree to receive test SMS messages.",
                              value=bool(contact.get("consent")))
        if st.form_submit_button("Save phone number"):
            try:
                sms.save_contact(username, phone, consent)
                st.session_state.pop("sms_attempt", None)
                st.session_state.pop("sms_submitted", None)
                st.session_state["sms_flash"] = "Phone settings saved."
                st.rerun()
            except ValueError as exc:
                st.error(str(exc))
    try:
        config = sms.ready_config()
    except ValueError as exc:
        st.info(str(exc))
        return
    trial = config["mode"] == "trial_template"
    st.markdown("##### Message")
    if trial:
        st.write("Twilio's predefined account-alert test message.")
        st.caption("Trial mode: verify your number in Twilio first. Twilio controls the wording. "
                   "Custom BloodSight donation messages require custom messaging to be enabled on the account.")
    else:
        st.write(sms.TEST_BODY)
    if contact.get("phone"):
        st.caption("To: " + contact["phone"])
    attempt = st.session_state.setdefault("sms_attempt", str(uuid.uuid4()))
    submitted = st.session_state.get("sms_submitted") == attempt
    enabled = bool(contact.get("phone") and contact.get("consent") and not submitted)
    if st.button("Send test SMS", type="primary", disabled=not enabled):
        # Mark before the call: a lost response must not turn a rerun into another send.
        st.session_state["sms_submitted"] = attempt
        try:
            with st.spinner("Sending test message..."):
                sms.send_test(username, attempt, contact["phone"])
            st.rerun()
        except ValueError as exc:
            st.error(str(exc))
    if submitted:
        if st.button("Prepare another test"):
            st.session_state["sms_attempt"] = str(uuid.uuid4())
            st.session_state.pop("sms_submitted", None)
            st.rerun()
    st.caption("Sends only when you press the button. Forecasts and donor requests do not send SMS automatically.")
    history = sms.history_for(username)
    if not history:
        return
    st.markdown("##### Recent tests")
    latest = history[0]
    st.write(sms.status_text(latest))
    if latest.get("provider_sid") and st.button("Check delivery"):
        try:
            sms.refresh_delivery(username, latest["id"])
            st.rerun()
        except ValueError as exc:
            st.error(str(exc))
    st.dataframe([{"Time (UTC)": r["created_at"], "Phone": "Ending " + r["phone"][-4:],
                   "Status": r["status"], "Reference": r.get("error_code") or ""} for r in history],
                 hide_index=True, use_container_width=True)
