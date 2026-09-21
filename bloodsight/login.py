"""Login page, demo account shortcuts, and first-open sign-up for a patient with a lab code."""

import streamlit as st

import store

DEMO = [("Blood centre", "centre", "centre123"), ("Lab / doctor", "lab", "lab123"), ("Patient", "patient", "patient123")]


def require_login() -> dict:
    """Return the logged-in user (fresh from the store), or render the login page and stop."""
    if "username" in st.session_state:
        user = store.get_user(st.session_state["username"])
        if user:
            return user
        del st.session_state["username"]

    _, mid, _ = st.columns([1, 1.2, 1])
    with mid:
        st.markdown("## 🩸 BloodSight AI")
        st.caption("Blood supply intelligence: see the shortage before it happens.")
        tab_in, tab_new = st.tabs(["Log in", "First time? Use your lab code"])
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
            st.caption("centre / centre123 · lab / lab123 · patient / patient123 (Alex, O-, donor part on) · "
                       "patient2 / patient123 (Sam, A+, results only)")
        with tab_new:
            _sign_up()
    st.stop()


def _sign_up() -> None:
    """Screen 4, first open: three questions and three switches. The lab code ties the app to one patient."""
    st.caption("Your lab code is printed on your lab letter. Demo codes that are still free: "
               + (", ".join(store.unclaimed_lab_codes()) or "none"))
    with st.form("signup"):
        lab_code = st.text_input("Your lab code", placeholder="e.g. BL-4821")
        name = st.text_input("Your name")
        c1, c2 = st.columns(2)
        username = c1.text_input("Choose a username")
        password = c2.text_input("Choose a password", type="password")
        blood_type = st.selectbox("Blood type", ["I do not know"] + store.BLOOD_TYPES,
                                  help="Unknown: your lab result fills it in.")
        postcode = st.text_input("Where do you live?", placeholder="Postcode, e.g. 6211")
        st.markdown("**What may the app do?**")
        s_results = st.toggle("Show me my lab results", value=True)
        s_nearby = st.toggle("Tell me when a place nearby needs my blood type", value=False)
        s_gave = st.toggle("Tell places I gave to before when I am allowed to give again", value=False)
        st.caption("Each switch can be turned off later under Me. Results only is a valid way to use the app.")
        go = st.form_submit_button("Continue", type="primary", use_container_width=True)
    if go:
        try:
            user = store.register_patient(lab_code, username, password, name, postcode,
                                          None if blood_type == "I do not know" else blood_type,
                                          {"results": s_results, "nearby": s_nearby, "gave_before": s_gave})
        except ValueError as e:
            st.error(str(e))
            return
        st.session_state["username"] = user["username"]
        st.rerun()
