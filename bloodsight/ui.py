"""Shared look: colors, status chips, CSS, page header, sidebar navigation."""

import streamlit as st

import store

# Chart + status colors (validated palette; status colors always ship with a dot + label).
BLUE, AQUA = "#2a78d6", "#1baf7a"
INK, INK_2, MUTED, GRID, AXIS = "#0b0b0b", "#52514e", "#898781", "#e1e0d9", "#c3c2b7"
STATUS = {
    "Critical": {"color": "#d03b3b", "icon": "🔴", "bg": "#fbeaea"},
    "Medium": {"color": "#b97d00", "icon": "🟡", "bg": "#fdf3d9"},
    "Low": {"color": "#0a7d0a", "icon": "🟢", "bg": "#e6f4e6"},
}
RISK_ORDER = {"Critical": 0, "Medium": 1, "Low": 2}


def dot(color: str, size: int = 8) -> str:
    """A small round status dot. Never shipped alone: it always sits next to a label."""
    return (f'<span style="display:inline-block;width:{size}px;height:{size}px;border-radius:50%;'
            f'background:{color};margin-right:6px;vertical-align:middle"></span>')


def css() -> None:
    # One stylesheet for the whole app: Inter everywhere, thin borders, 8px radii, readable tables,
    # and a sidebar whose account block sits at the bottom. No CSS comments in the block below:
    # Streamlit renders it through markdown, and a comment marker cuts the style tag short.
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
    h1, h2, h3, h4, h5, h6 {font-weight: 600 !important; letter-spacing: -0.012em !important; color: #0b0b0b;}
    h2 {font-size: 1.6rem !important;}
    h3 {font-size: 1.25rem !important;}
    body, p, li, .stMarkdown {font-size: .95rem; line-height: 1.55;}
    button {font-weight: 500 !important; letter-spacing: 0 !important;}
    .stButton button, .stFormSubmitButton button {border-radius: 8px !important; border-width: 1px !important;}
    input, textarea, .stTextInput input, .stSelectbox div[data-baseweb="select"] > div {
        border-radius: 8px !important;
    }
    .block-container {padding-top: 2.2rem; max-width: 1400px;}
    .bs-grid {display: grid; grid-template-columns: repeat(auto-fit, minmax(140px, 1fr)); gap: 10px;}
    .bs-card {border: 1px solid #e1e0d9; border-radius: 8px; padding: 16px 18px; background: #fff;}
    .bs-card .bt {font-size: 1.35rem; font-weight: 600; color: #0b0b0b;}
    .bs-card .units {font-size: .95rem; color: #52514e; margin: 2px 0 8px;}
    .bs-card .units b {color: #0b0b0b; font-size: 1.15rem; font-weight: 600;}
    .bs-chip {display: inline-block; border-radius: 999px; padding: 2px 10px; font-size: .8rem; font-weight: 600;}
    .bs-card .sub {font-size: .8rem; color: #5f5d58; margin-top: 8px;}
    .bs-alert {border-left: 4px solid #d03b3b; background: #fbeaea; border-radius: 8px; padding: 14px 18px; margin: 6px 0 4px;}
    .bs-alert.ok {border-color: #0a7d0a; background: #e6f4e6;}
    .bs-alert h4 {margin: 0 0 4px; color: #0b0b0b;}
    .bs-alert p {margin: 0; color: #52514e;}
    .bs-rec {border: 1px solid #e1e0d9; border-radius: 8px; padding: 16px 18px; background: #fff;}
    .bs-rec table {width: 100%; border-collapse: collapse; margin-top: 8px;}
    .bs-rec td {padding: 5px 0; border-top: 1px solid #f0efec; color: #52514e;}
    .bs-rec td:last-child {text-align: right; font-weight: 600; color: #0b0b0b;}
    .stMarkdown table {width: 100%; border-collapse: collapse; margin: 6px 0 10px;}
    .stMarkdown table th, .stMarkdown table td {
        padding: 10px 14px !important; text-align: left !important; vertical-align: top;
        border-bottom: 1px solid #ecece6; font-size: .92rem;
    }
    .stMarkdown table th {
        text-transform: uppercase; font-size: .72rem !important; letter-spacing: .05em;
        color: #6b6963; font-weight: 600; border-bottom: 1px solid #e1e0d9;
    }
    .stMarkdown table td {color: #35342f;}
    .bs-rec table td {padding: 6px 0 !important;}
    .bs-legal {margin-top: 26px; padding-top: 14px; border-top: 1px solid #e1e0d9; color: #8a8882; font-size: .68rem;
               line-height: 1.5;}
    .bs-legal-h {font-weight: 600; font-size: .72rem; color: #6b6963; letter-spacing: .02em; margin-bottom: 2px;}
    .bs-legal-lead {margin-bottom: 10px;}
    .bs-legal-grid {display: grid; grid-template-columns: repeat(3, 1fr); gap: 14px; margin-bottom: 10px;}
    .bs-legal-grid b {color: #6b6963; font-weight: 600;}
    .bs-legal-foot {color: #9b9993;}
    @media (max-width: 820px) {.bs-legal-grid {grid-template-columns: 1fr;}}
    [data-testid="stSidebarContent"] {display: flex; flex-direction: column;}
    [data-testid="stSidebarUserContent"] {display: flex; flex-direction: column; flex: 1 1 auto;}
    [data-testid="stSidebarUserContent"] > div {display: flex; flex-direction: column; flex: 1 1 auto;}
    [data-testid="stSidebarUserContent"] > div > div[data-testid="stVerticalBlock"] {
        display: flex; flex-direction: column; flex: 1 1 auto; min-height: calc(100vh - 9rem);
    }
    [data-testid="stSidebarUserContent"] > div > div[data-testid="stVerticalBlock"] > div:last-child {
        margin-top: auto;
    }
    [data-testid="stSidebar"] {border-right: 1px solid #e1e0d9;}
    </style>
    """, unsafe_allow_html=True)


def chip(risk: str, label: str | None = None) -> str:
    """Status chip. Status colors always ship with a dot and a label, never color alone."""
    s = STATUS[risk]
    return (f'<span class="bs-chip" style="background:{s["bg"]};color:{s["color"]}">'
            f'{dot(s["color"])}{label or risk}</span>')


def sidebar(user: dict, pages: list[str]) -> str:
    """Sidebar navigation for a role. Returns the selected page. To jump: set st.session_state["_goto"], then st.rerun()."""
    with st.sidebar:
        st.markdown("### BloodSight AI")
        st.caption(f"{user.get('title') or 'Donor of ' + store.LAB_NAME}")
        # Page jumps: a view sets st.session_state["_goto"] = "<page>" and calls st.rerun(). Writing "nav"
        # directly after this radio exists raises StreamlitAPIException, so the jump is applied here, before it.
        goto = st.session_state.pop("_goto", None)
        if goto in pages:
            st.session_state["nav"] = goto
        if st.session_state.get("nav") not in pages:
            st.session_state["nav"] = pages[0]
        page = st.radio("Go to", pages, key="nav", label_visibility="collapsed")
        # The account block is the last child of the sidebar, so the CSS above pushes it to the bottom.
        with st.container():
            st.divider()
            unread = store.unread_count(user["username"])
            st.markdown(f"**{user['name']}**")
            st.caption(f"{unread} unread notification{'s' if unread != 1 else ''}" if unread
                       else "No unread notifications")
            if st.button("Log out", key="logout", use_container_width=True):
                for k in list(st.session_state.keys()):
                    del st.session_state[k]
                st.rerun()
    return page


def header(title: str, subtitle: str | None = None) -> None:
    left, right = st.columns([3, 1.4], vertical_alignment="center")
    left.markdown(f"## {title}")
    if subtitle:
        left.caption(subtitle)
    right.markdown(f"<div style='text-align:right;color:{MUTED}'>{store.today():%A, %d %B %Y}</div>",
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
