"""Shared look: colors, status marks, CSS, page header, sidebar navigation."""

import streamlit as st

import store

# Chart + status colors (validated palette; a status always ships as a dot plus a label).
BLUE, AQUA = "#1d4ed8", "#15803d"
INK, INK_2, MUTED, GRID, AXIS = "#111827", "#4b5563", "#6b7280", "#e5e4df", "#c3c2b7"
STATUS = {
    "Critical": {"color": "#c8102e", "icon": "", "bg": "#fdecef"},
    "Medium": {"color": "#b45309", "icon": "", "bg": "#fdf4e7"},
    "Low": {"color": "#15803d", "icon": "", "bg": "#eaf5ec"},
}
RISK_ORDER = {"Critical": 0, "Medium": 1, "Low": 2}

NAV_ICONS = {
    "SMS test": "sms",
    "Outlook": "monitoring", "Requests": "campaign", "Bookings": "event_available",
    "Network": "hub", "Hospital orders": "local_shipping", "Notifications": "notifications",
    "Publish results": "task", "Patients": "group", "Blood requests": "bloodtype",
    "Notify patients": "send", "Donor link": "link", "Results": "lab_panel",
    "Needs": "volunteer_activism", "Donations": "history", "Ask": "chat", "Me": "person",
}


def dot(color: str, size: int = 6) -> str:
    """A small round status dot. Never shipped alone: it always sits next to a label."""
    return (f'<span style="display:inline-block;width:{size}px;height:{size}px;border-radius:50%;'
            f'background:{color};margin-right:6px;vertical-align:middle"></span>')


LOGO = ('<svg width="22" height="22" viewBox="0 0 24 24" aria-hidden="true">'
        '<path fill="#c8102e" d="M12 2.2c3.4 4.3 6.6 8 6.6 11.9a6.6 6.6 0 1 1-13.2 0C5.4 10.2 8.6 6.5 12 2.2z"/></svg>')


def css() -> None:
    # One stylesheet for the whole app. No CSS comments and no blank lines inside the style block:
    # Streamlit renders it through markdown, and either one cuts the style tag short.
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
    html, body, [class*="st-"], .stMarkdown, .stMarkdown div, .stMarkdown span, button, input, textarea, select,
    table, th, td, h1, h2, h3, h4, h5, h6, p, li, label, div[data-testid="stMetricValue"] {
        font-family: 'Inter', system-ui, -apple-system, 'Segoe UI', Roboto, sans-serif !important;
        font-feature-settings: 'tnum' 0;
        -webkit-font-smoothing: antialiased;
    }
    [data-testid="stIconMaterial"], .material-symbols-rounded, span[class^="material-"], span[class*=" material-"] {
        font-family: 'Material Symbols Rounded' !important;
    }
    h1, h2, h3, h4, h5, h6 {font-weight: 600 !important; letter-spacing: -0.012em !important; color: #111827;}
    h2 {font-size: 20px !important; line-height: 1.3 !important; margin: 0 0 2px !important;}
    h3 {font-size: 15px !important; margin: 0 0 4px !important;}
    body, p, li, .stMarkdown {font-size: 14px; line-height: 1.55; color: #111827;}
    .block-container {padding-top: 4.4rem; padding-bottom: 3rem; max-width: 1400px; animation: bsfade .22s ease-out;}
    @keyframes bsfade {from {opacity: 0; transform: translateY(4px);} to {opacity: 1; transform: none;}}
    [data-stale="true"] {opacity: 0 !important; transition: none !important;}
    [data-testid="stHeader"] {background: transparent;}
    [data-testid="stChatMessageAvatarUser"], [data-testid="stChatMessageAvatarAssistant"], [data-testid="stChatMessage"] > div:first-child:has(svg) {display: none !important;}
    [data-testid="stChatMessage"] {background: transparent !important; padding: 6px 0 !important; border-bottom: 1px solid #ecebe6; border-radius: 0 !important;}
    [data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarUser"]) p {font-weight: 600;}
    [data-testid="stBaseButton-primary"] p, [data-testid="stBaseButton-primary"] span, [data-testid="stBaseButton-primary"] div,
    [data-testid="stBaseButton-primaryFormSubmit"] p, [data-testid="stBaseButton-primaryFormSubmit"] span, [data-testid="stBaseButton-primaryFormSubmit"] div,
    [data-testid="stBaseButton-primaryDownload"] p, [data-testid="stBaseButton-primaryDownload"] span {color: #ffffff !important;}
    [data-testid="stBaseButton-primary"]:disabled, [data-testid="stBaseButton-primaryFormSubmit"]:disabled {background: #e9b7bf !important; border-color: #e9b7bf !important;}
    [data-testid="stBaseButton-primary"], [data-testid="stBaseButton-secondary"],
    [data-testid="stBaseButton-primaryFormSubmit"], [data-testid="stBaseButton-secondaryFormSubmit"],
    [data-testid="stDownloadButton"] button, [data-testid="stBaseButton-secondaryDownload"],
    [data-testid="stBaseButton-primaryDownload"] {
        height: 36px !important; min-height: 36px !important; border-radius: 6px !important;
        font-size: 13.5px !important; font-weight: 500 !important; line-height: 1 !important;
        padding: 0 14px !important; box-shadow: none !important; letter-spacing: 0 !important;
        white-space: nowrap;
    }
    [data-testid="stBaseButton-primary"], [data-testid="stBaseButton-primaryFormSubmit"],
    [data-testid="stBaseButton-primaryDownload"] {
        background: #c8102e !important; border: 1px solid #c8102e !important; color: #ffffff !important;
    }
    [data-testid="stBaseButton-primary"]:hover, [data-testid="stBaseButton-primaryFormSubmit"]:hover,
    [data-testid="stBaseButton-primaryDownload"]:hover, [data-testid="stBaseButton-primary"]:focus,
    [data-testid="stBaseButton-primaryFormSubmit"]:focus {
        background: #a50d26 !important; border-color: #a50d26 !important; color: #ffffff !important;
    }
    [data-testid="stBaseButton-secondary"], [data-testid="stBaseButton-secondaryFormSubmit"],
    [data-testid="stDownloadButton"] button, [data-testid="stBaseButton-secondaryDownload"] {
        background: #ffffff !important; border: 1px solid #d4d3cd !important; color: #111827 !important;
    }
    [data-testid="stBaseButton-secondary"]:hover, [data-testid="stBaseButton-secondaryFormSubmit"]:hover,
    [data-testid="stDownloadButton"] button:hover, [data-testid="stBaseButton-secondaryDownload"]:hover {
        border-color: #9ca3af !important; color: #111827 !important; background: #ffffff !important;
    }
    [data-testid="stButton"], [data-testid="stDownloadButton"] {width: auto !important;}
    [data-testid="stButton"] button, [data-testid="stDownloadButton"] button {width: auto !important;}
    [data-testid="stForm"] [data-testid="stFormSubmitButton"] button {width: auto;}
    [data-testid="stMetric"] {background: transparent !important; border: 0 !important; padding: 0 !important;}
    [data-testid="stMetricLabel"], [data-testid="stMetricLabel"] p {
        font-size: 12px !important; font-weight: 500 !important; color: #6b7280 !important; line-height: 1.3 !important;
    }
    [data-testid="stMetricValue"] {
        font-size: 24px !important; font-weight: 600 !important; color: #111827 !important; line-height: 1.25 !important;
    }
    [data-testid="stMetricDelta"], [data-testid="stMetricDelta"] div {font-size: 12px !important;}
    input, textarea, .stTextInput input, .stSelectbox div[data-baseweb="select"] > div {border-radius: 6px !important;}
    .bs-grid {display: grid; grid-template-columns: repeat(auto-fit, minmax(140px, 1fr)); gap: 10px;}
    .bs-card {border: 1px solid #e5e4df; border-radius: 10px; padding: 16px 18px; background: #fff; box-shadow: none;}
    .bs-card .bt {font-size: 15px; font-weight: 600; color: #111827;}
    .bs-card .units {font-size: 13px; color: #4b5563; margin: 2px 0 8px;}
    .bs-card .units b {color: #111827; font-size: 14px; font-weight: 600;}
    .bs-card .sub {font-size: 12.5px; color: #6b7280; margin-top: 8px;}
    .bs-alert {border: 1px solid #e5e4df; background: #fff; border-radius: 10px; padding: 14px 18px; margin: 6px 0 4px;}
    .bs-alert h4 {margin: 0 0 4px; color: #111827; font-size: 15px; font-weight: 600;}
    .bs-alert p {margin: 0; color: #4b5563; font-size: 13.5px;}
    .bs-rec {border: 1px solid #e5e4df; border-radius: 10px; padding: 16px 18px; background: #fff; box-shadow: none;}
    .bs-rec table {width: 100%; border-collapse: collapse; margin-top: 8px;}
    .bs-rec td {padding: 6px 0 !important; border-top: 1px solid #f0efec; color: #4b5563; font-size: 13px;}
    .bs-rec td:last-child {text-align: right; font-weight: 600; color: #111827;}
    .bs-mark {font-size: 12.5px; font-weight: 600; white-space: nowrap;}
    .stMarkdown table {width: 100%; border-collapse: collapse; margin: 6px 0 10px; border: 0;}
    .stMarkdown table th, .stMarkdown table td {
        padding: 8px 12px !important; text-align: left !important; vertical-align: top;
        border-bottom: 1px solid #ecece6; border-left: 0; border-right: 0; font-size: 13px;
    }
    .stMarkdown table th {
        text-transform: uppercase; font-size: 11.5px !important; letter-spacing: .04em;
        color: #6b7280; font-weight: 600; border-bottom: 1px solid #e5e4df; background: transparent;
    }
    .stMarkdown table td {color: #111827;}
    .stMarkdown table tr:last-child td {border-bottom: 0;}
    .bs-legal {margin-top: 26px; padding-top: 14px; border-top: 1px solid #e5e4df; color: #8a8882; font-size: 11px;
               line-height: 1.5;}
    .bs-legal-h {font-weight: 600; font-size: 11.5px; color: #6b7280; letter-spacing: .02em; margin-bottom: 2px;}
    .bs-legal-lead {margin-bottom: 10px;}
    .bs-legal-grid {display: grid; grid-template-columns: repeat(3, 1fr); gap: 14px; margin-bottom: 10px;}
    .bs-legal-grid b {color: #6b7280; font-weight: 600;}
    .bs-legal-foot {color: #9b9993;}
    @media (max-width: 820px) {.bs-legal-grid {grid-template-columns: 1fr;}}
    [data-testid="stSidebarContent"] {display: flex; flex-direction: column;}
    [data-testid="stSidebarUserContent"] {display: flex; flex-direction: column; flex: 1 1 auto; padding-top: 1rem;}
    [data-testid="stSidebarUserContent"] > div {display: flex; flex-direction: column; flex: 1 1 auto;}
    [data-testid="stSidebarUserContent"] > div > div[data-testid="stVerticalBlock"] {
        display: flex; flex-direction: column; flex: 1 1 auto; min-height: calc(100vh - 7rem);
    }
    [data-testid="stSidebarUserContent"] > div > div[data-testid="stVerticalBlock"] > div:last-child {
        margin-top: auto;
    }
    [data-testid="stSidebar"] {background: #ffffff; min-width: 244px; max-width: 244px; border-right: 1px solid #e5e4df;}
    [data-testid="stSidebar"] .bs-brand {display: flex; align-items: center; gap: 8px; font-size: 16px; font-weight: 600; color: #111827; letter-spacing: -0.01em; padding: 0 4px;}
    [data-testid="stSidebar"] .bs-brand b {color: #c8102e; font-weight: 600; margin-left: 3px;}
    [data-testid="stSidebar"] .bs-org {font-size: 12px; color: #6b7280; padding: 3px 4px 12px; border-bottom: 1px solid #ecebe6;}
    [data-testid="stSidebar"] .bs-navlabel {font-size: 10.5px; letter-spacing: .09em; text-transform: uppercase; color: #9ca3af; padding: 14px 4px 4px;}
    [data-testid="stSidebar"] [data-testid="stRadio"], [data-testid="stSidebar"] [data-testid="stRadio"] > div,
    [data-testid="stSidebar"] [role="radiogroup"], [data-testid="stSidebar"] [role="radiogroup"] > div {width: 100%;}
    [data-testid="stSidebar"] [role="radiogroup"] {gap: 1px;}
    [data-testid="stSidebar"] label[data-testid="stRadioOption"] {
        width: 100%; box-sizing: border-box; display: flex !important; align-items: center;
        min-height: 34px; height: 34px; padding: 0 9px; border-radius: 6px; cursor: pointer; margin: 0;
    }
    [data-testid="stSidebar"] label[data-testid="stRadioOption"] > div {width: 100%; gap: 0; align-items: center;}
    [data-testid="stSidebar"] label[data-testid="stRadioOption"] > div > div:first-child {display: none !important;}
    [data-testid="stSidebar"] label[data-testid="stRadioOption"] > div > div[data-testid="stMarkdownContainer"] {display: block !important; padding-left: 0; margin-left: 0;}
    [data-testid="stSidebar"] label[data-testid="stRadioOption"] p {
        font-size: 13.5px; color: #4b5563; display: flex; align-items: center; gap: 9px; margin: 0; line-height: 1;
    }
    [data-testid="stSidebar"] label[data-testid="stRadioOption"] [data-testid="stIconMaterial"] {
        font-size: 18px !important; width: 18px; color: #9ca3af; flex: none;
    }
    [data-testid="stSidebar"] label[data-testid="stRadioOption"]:hover {background: #f3f2ee;}
    [data-testid="stSidebar"] label[data-testid="stRadioOption"][data-selected="true"] {background: #fdecef;}
    [data-testid="stSidebar"] label[data-testid="stRadioOption"][data-selected="true"] p {color: #a50d26; font-weight: 600;}
    [data-testid="stSidebar"] label[data-testid="stRadioOption"][data-selected="true"] [data-testid="stIconMaterial"] {color: #a50d26;}
    [data-testid="stSidebar"] .bs-account {display: flex; align-items: center; gap: 10px; padding: 12px 4px 4px; border-top: 1px solid #ecebe6;}
    [data-testid="stSidebar"] .bs-avatar {width: 30px; height: 30px; border-radius: 50%; background: #111827; color: #fff; font-size: 11px; font-weight: 600; display: flex; align-items: center; justify-content: center; flex: none;}
    [data-testid="stSidebar"] .bs-acc-name {font-size: 13px; font-weight: 600; color: #111827; line-height: 1.2;}
    [data-testid="stSidebar"] .bs-acc-sub {font-size: 11.5px; color: #6b7280;}
    [data-testid="stSidebar"] .st-key-logout {width: auto !important; margin-left: 1px;}
    [data-testid="stSidebar"] .st-key-logout button {
        background: transparent !important; border: 0 !important; color: #6b7280 !important;
        font-size: 12.5px !important; height: 28px !important; min-height: 28px !important; padding: 0 3px !important;
        justify-content: flex-start !important; width: auto !important;
    }
    [data-testid="stSidebar"] .st-key-logout button:hover {color: #a50d26 !important; text-decoration: underline;}
    </style>
    """, unsafe_allow_html=True)


def chip(risk: str, label: str | None = None) -> str:
    """Status mark: a 6px dot plus plain coloured text. Never a pill, never colour alone."""
    s = STATUS[risk]
    return (f'<span class="bs-mark" style="color:{s["color"]}">'
            f'{dot(s["color"])}{label or risk}</span>')


def sidebar(user: dict, pages: list[str]) -> str:
    """Sidebar navigation for a role. Returns the selected page. To jump: set st.session_state["_goto"], then st.rerun()."""
    with st.sidebar:
        st.markdown(f'<div class="bs-brand">{LOGO}<span>BloodSight<b>AI</b></span></div>'
                    f'<div class="bs-org">{user.get("title") or "Donor of " + store.LAB_NAME}</div>'
                    '<div class="bs-navlabel">Workspace</div>', unsafe_allow_html=True)
        # Page jumps: a view sets st.session_state["_goto"] = "<page>" and calls st.rerun(). Writing "nav"
        # directly after this radio exists raises StreamlitAPIException, so the jump is applied here, before it.
        goto = st.session_state.pop("_goto", None)
        if goto in pages:
            st.session_state["nav"] = goto
        if st.session_state.get("nav") not in pages:
            st.session_state["nav"] = pages[0]
        page = st.radio("Go to", pages, key="nav", label_visibility="collapsed",
                        format_func=lambda p: f":material/{NAV_ICONS.get(p, 'chevron_right')}: {p}")
        # The account block is the last child of the sidebar, so the CSS pushes it to the bottom.
        with st.container():
            unread = store.unread_count(user["username"])
            initials = "".join(w[0] for w in user["name"].replace("Dr. ", "").split()[:2]).upper()
            note = f"{unread} unread" if unread else "No unread notifications"
            st.markdown(f'<div class="bs-account"><div class="bs-avatar">{initials}</div>'
                        f'<div><div class="bs-acc-name">{user["name"]}</div>'
                        f'<div class="bs-acc-sub">{note}</div></div></div>', unsafe_allow_html=True)
            if st.button("Log out", key="logout"):
                for k in list(st.session_state.keys()):
                    del st.session_state[k]
                st.rerun()
    return page


def header(title: str, subtitle: str | None = None) -> None:
    left, right = st.columns([3, 1.4], vertical_alignment="center")
    left.markdown(f"<div style='font-size:20px;font-weight:600;color:{INK};line-height:1.3'>{title}</div>",
                  unsafe_allow_html=True)
    if subtitle:
        left.markdown(f"<div style='font-size:12.5px;color:{MUTED};margin-top:2px'>{subtitle}</div>",
                      unsafe_allow_html=True)
    right.markdown(f"<div style='text-align:right;color:{MUTED};font-size:12.5px'>{store.today():%A, %d %B %Y}</div>",
                   unsafe_allow_html=True)


def notification_list(username: str, empty: str = "Nothing yet.") -> None:
    """Inbox: newest first, unread marked, one button to mark all as read."""
    items = store.notifications(username)
    if not items:
        st.caption(empty)
        return
    if any(not n["read"] for n in items) and st.button("Mark all as read", key="mark_all_read"):
        store.mark_read(username)
        st.rerun()
    for n in items:
        mark = dot(BLUE) if not n["read"] else ""
        st.markdown(f'<div class="bs-card" style="margin-bottom:8px"><b>{mark}{n["title"]}</b>'
                    f'<div class="units">{n["body"]}</div>'
                    f'<div class="sub">{n["from"]} · {n["created_at"][11:16]}</div></div>', unsafe_allow_html=True)
