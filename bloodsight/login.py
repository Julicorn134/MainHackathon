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


BRAND = """
<div class="bs-brand">
  <svg class="bs-drop" width="34" height="34" viewBox="0 0 24 24" aria-hidden="true">
    <path fill="#c8102e" d="M12 2.2c4.2 5 7 8.6 7 12.1a7 7 0 0 1-14 0c0-3.5 2.8-7.1 7-12.1z"/>
  </svg>
  <span class="bs-word">BloodSight <span class="bs-ai">AI</span></span>
</div>
<div class="bs-sub">Sign in to your workspace</div>
"""

CSS = """
<style>
.block-container {padding-top: 6vh;}
.st-key-login_card {max-width: 440px; margin: 0 auto; background: #ffffff; border: 1px solid #e1e0d9; border-radius: 12px; padding: 28px; box-shadow: 0 1px 2px rgba(0,0,0,.04), 0 8px 24px rgba(0,0,0,.06);}
.st-key-login_card [data-testid="stForm"] {border: 0; padding: 0; background: transparent;}
.bs-brand {display: flex; align-items: center; justify-content: center; gap: 10px;}
.bs-drop {flex: none; display: block;}
.bs-word {font-size: 1.6rem; font-weight: 650; letter-spacing: -.01em; color: #1b1b1a; line-height: 1;}
.bs-ai {color: #c8102e;}
.bs-sub {text-align: center; font-size: .85rem; color: #6b6b66; margin: 6px 0 18px;}
.st-key-login_card [data-testid="stTextInputRootElement"] {height: 44px; border-radius: 8px; border: 1px solid #d9d8d1; background: #ffffff;}
.st-key-login_card [data-testid="stTextInputRootElement"]:focus-within {border-color: #c8102e;}
.st-key-login_card [data-testid="stTextInputField"] {height: 42px; border-radius: 8px;}
.st-key-login_card [data-testid="stSelectbox"] [data-testid="stSelectboxRootElement"] {min-height: 44px; border-radius: 8px; border: 1px solid #d9d8d1;}
.st-key-login_card [data-testid="stBaseButton-primaryFormSubmit"] {width: 100%; height: 44px; border-radius: 8px; background: #c8102e; border: 1px solid #c8102e; color: #ffffff; font-weight: 600;}
.st-key-login_card [data-testid="stBaseButton-primaryFormSubmit"]:hover, .st-key-login_card [data-testid="stBaseButton-primaryFormSubmit"]:focus {background: #a80d26; border-color: #a80d26; color: #ffffff;}
.st-key-login_card [role="tablist"] {gap: 22px; border-bottom: 1px solid #e1e0d9; margin-bottom: 16px;}
.st-key-login_card [data-testid="stTab"] {padding: 6px 0; background: transparent;}
.st-key-login_card [data-testid="stTab"] .react-aria-SelectionIndicator {background: #c8102e; background-color: #c8102e;}
.st-key-login_card [data-testid="stTab"][aria-selected="true"] p {color: #c8102e; font-weight: 600;}
.bs-rule {border-top: 1px solid #ebeae4; margin: 20px 0 12px;}
.bs-demo-label {font-size: .7rem; letter-spacing: .08em; text-transform: uppercase; color: #8a8a83; margin-bottom: 8px;}
.st-key-login_card [data-testid="stButton"] button {height: 40px; border-radius: 8px; border: 1px solid #e1e0d9; background: #fbfbf9; color: #33332f; font-weight: 500;}
.st-key-login_card [data-testid="stButton"] button:hover {border-color: #c8102e; color: #c8102e;}
.bs-legal {max-width: 560px; margin: 22px auto 0; text-align: center;}
</style>
"""


def require_login() -> dict:
    """Return the logged-in user (fresh from the store), or render the login page and stop."""
    if "username" in st.session_state:
        user = store.get_user(st.session_state["username"])
        if user:
            return user
        del st.session_state["username"]

    st.markdown(CSS, unsafe_allow_html=True)
    _, mid, _ = st.columns([1, 1.2, 1])
    with mid:
        with st.container(border=True, key="login_card"):
            st.markdown(BRAND, unsafe_allow_html=True)
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
                st.markdown('<div class="bs-rule"></div><div class="bs-demo-label">Demo accounts</div>',
                            unsafe_allow_html=True)
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
