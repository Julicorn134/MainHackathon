"""BloodSight AI. Run with: streamlit run app.py

Three sides, one spine: the blood centre sees a shortage before it happens, and the request
reaches the right people in time. Each role has its own view module in views/.
"""

import streamlit as st

import login
import ui
from storage_config import StorageUnavailable

st.set_page_config(page_title="BloodSight AI", page_icon="🩸", layout="wide", initial_sidebar_state="collapsed")
ui.css()

try:
    user = login.require_login()

    # Views are imported per role, so one side's code never runs for another side's user.
    if user["role"] == "centre":
        from views import centre as view
    elif user["role"] == "lab":
        from views import lab as view
    else:
        from views import patient as view
    view.render(user)
except StorageUnavailable as exc:
    st.error(str(exc))
    st.info("Cloud data is unavailable. Check server settings or retry when the connection is restored.")
    st.button("Retry connection", on_click=lambda: None)
