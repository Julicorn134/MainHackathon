"""Login page, demo account shortcuts, and first-open sign-up. The lab code is entered later, inside the app."""

import streamlit as st

import store

DEMO = [("Blood centre", "centre", "centre123"), ("Lab", "lab", "lab123"), ("Donor", "patient", "patient123")]

LEGAL = """
<div class="bs-legal">
  <div class="bs-legal-h">Secure &amp; Compliant</div>
  <div class="bs-legal-lead">Your data security and privacy matter to us.</div>
  <div class="bs-legal-grid">
    <div><b>GDPR &amp; Data Protection:</b> We are committed to protecting personal data and supporting
      applicable data protection requirements.</div>
    <div><b>Secure Data Transmission:</b> Data is protected in transit using industry-standard
      encryption protocols.</div>
    <div><b>Privacy &amp; Access Control:</b> Access to organizational data is managed through
      authentication and appropriate access controls.</div>
  </div>
  <div class="bs-legal-foot">By signing in, you agree to our Terms of Service and Privacy Policy.
    For more information, visit our Security &amp; Compliance page.</div>
</div>
"""


def require_login() -> dict:
    """Return the logged-in user (fresh from the store), or render the login page and stop."""
    if "username" in st.session_state:
        user = store.get_user(st.session_state["username"])
        if user:
            return user
        del st.session_state["username"]

    _, mid, _ = st.columns([1, 1.2, 1])
    with mid:
        st.markdown("## BloodSight AI")
        tab_in, tab_new = st.tabs(["Log in", "Sign up"])
        with tab_in:
            with st.form("login"):
                username = st.text_input("Username")
                password = st.text_input("Password", type="password")
                submitted = st.form_submit_button("Log in", type="primary", use_container_width=True)
            if submitted:
                user = store.authenticate(username, password)
                if user:
                    st.session_state["username"] = user["username"]
                    st.rerun()
                st.error("Unknown username or wrong password.")
            st.markdown("###### Demo accounts")
            for col, (label, u, pw) in zip(st.columns(len(DEMO)), DEMO):
                if col.button(label, use_container_width=True, help=f"{u} / {pw}", key=f"demo_{u}"):
                    st.session_state["username"] = u
                    st.rerun()
        with tab_new:
            _sign_up()
        st.markdown(LEGAL, unsafe_allow_html=True)
    st.stop()


def _sign_up() -> None:
    """First open: who you are and what the app may do. The lab code is added later, inside the app."""
    with st.form("signup"):
        name = st.text_input("Your name")
        c1, c2 = st.columns(2)
        username = c1.text_input("Choose a username")
        password = c2.text_input("Choose a password", type="password")
        postcode = st.text_input("Where do you live?", placeholder="Postcode, e.g. 6211")
        blood_type = st.selectbox("Blood type", ["I do not know"] + store.BLOOD_TYPES,
                                  help="Unknown: your lab result fills it in.")
        st.markdown("**What may the app do?**")
        s_results = st.toggle("Show me my lab results", value=True)
        s_nearby = st.toggle("Tell me when a place nearby needs my blood type", value=False)
        s_gave = st.toggle("Tell places I gave to before when I am allowed to give again", value=False)
        st.caption("Each switch can be turned off later under Me. Results only is a valid way to use the app.")
        go = st.form_submit_button("Continue", type="primary", use_container_width=True)
    if go:
        try:
            user = store.register_patient("", username, password, name, postcode,
                                          None if blood_type == "I do not know" else blood_type,
                                          {"results": s_results, "nearby": s_nearby, "gave_before": s_gave})
        except ValueError as e:
            st.error(str(e))
            return
        st.session_state["username"] = user["username"]
        st.rerun()
