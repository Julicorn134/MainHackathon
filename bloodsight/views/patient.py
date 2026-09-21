"""Patient side: Results, Needs, Donations, Ask, Notifications, Me."""

import streamlit as st

import store
import ui

PAGES = ['Results', 'Needs', 'Donations', 'Ask', 'Notifications', 'Me']


def render(user: dict) -> None:
    page = ui.sidebar(user, PAGES)
    ui.header(page)
    st.info("Not built yet.")
