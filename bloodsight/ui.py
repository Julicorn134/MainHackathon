"""Shared look: colors, status chips, CSS, page header, sidebar navigation."""

import streamlit as st

import store

# Chart + status colors (validated palette; status colors always ship with icon + label).
BLUE, AQUA = "#2a78d6", "#1baf7a"
INK, INK_2, MUTED, GRID, AXIS = "#0b0b0b", "#52514e", "#898781", "#e1e0d9", "#c3c2b7"
STATUS = {
    "Critical": {"color": "#d03b3b", "icon": "🔴", "bg": "#fbeaea"},
    "Medium": {"color": "#b97d00", "icon": "🟡", "bg": "#fdf3d9"},
    "Low": {"color": "#0a7d0a", "icon": "🟢", "bg": "#e6f4e6"},
}
RISK_ORDER = {"Critical": 0, "Medium": 1, "Low": 2}



def css() -> None:
    st.markdown("""
    <style>
    .block-container {padding-top: 2.2rem; max-width: 1400px;}
    .bs-grid {display: grid; grid-template-columns: repeat(auto-fit, minmax(140px, 1fr)); gap: 10px;}
    .bs-card {border: 1px solid #e1e0d9; border-radius: 10px; padding: 12px 14px; background: #fff;}
    .bs-card .bt {font-size: 1.35rem; font-weight: 700; color: #0b0b0b;}
    .bs-card .units {font-size: .95rem; color: #52514e; margin: 2px 0 8px;}
    .bs-card .units b {color: #0b0b0b; font-size: 1.15rem;}
    .bs-chip {display: inline-block; border-radius: 999px; padding: 2px 10px; font-size: .8rem; font-weight: 600;}
    .bs-card .sub {font-size: .8rem; color: #5f5d58; margin-top: 8px;}  /* 6.5:1 on white: it carries the "why you" line */
    .bs-alert {border-left: 5px solid #d03b3b; background: #fbeaea; border-radius: 8px; padding: 14px 18px; margin: 6px 0 4px;}
    .bs-alert.ok {border-color: #0a7d0a; background: #e6f4e6;}
    .bs-alert h4 {margin: 0 0 4px; color: #0b0b0b;}
    .bs-alert p {margin: 0; color: #52514e;}
    .bs-rec {border: 1px solid #e1e0d9; border-radius: 10px; padding: 16px 18px; background: #fff;}
    .bs-rec table {width: 100%; border-collapse: collapse; margin-top: 8px;}
    .bs-rec td {padding: 5px 0; border-top: 1px solid #f0efec; color: #52514e;}
    .bs-rec td:last-child {text-align: right; font-weight: 700; color: #0b0b0b;}
    </style>
    """, unsafe_allow_html=True)


def chip(risk: str, label: str | None = None) -> str:
    """Status chip. Status colors always ship with an icon and a label, never color alone."""
    s = STATUS[risk]
    return f'<span class="bs-chip" style="background:{s["bg"]};color:{s["color"]}">{s["icon"]} {label or risk}</span>'


def sidebar(user: dict, pages: list[str]) -> str:
    """Sidebar navigation for a role. Returns the selected page. To jump: set st.session_state["_goto"], then st.rerun()."""
    with st.sidebar:
        st.markdown("### 🩸 BloodSight AI")
        st.caption(f"{user.get('title') or 'Patient of ' + store.LAB_NAME}")
        # Page jumps: a view sets st.session_state["_goto"] = "<page>" and calls st.rerun(). Writing "nav"
        # directly after this radio exists raises StreamlitAPIException, so the jump is applied here, before it.
        goto = st.session_state.pop("_goto", None)
        if goto in pages:
            st.session_state["nav"] = goto
        if st.session_state.get("nav") not in pages:
            st.session_state["nav"] = pages[0]
        page = st.radio("Go to", pages, key="nav", label_visibility="collapsed")
        st.divider()
        unread = store.unread_count(user["username"])
        st.markdown(f"**{user['name']}**")
        st.caption(f"{unread} unread notification{'s' if unread != 1 else ''}" if unread else "No unread notifications")
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
        dot = "🔵 " if not n["read"] else ""
        st.markdown(f'<div class="bs-card" style="margin-bottom:8px"><b>{dot}{n["title"]}</b>'
                    f'<div class="units">{n["body"]}</div>'
                    f'<div class="sub">{n["from"]} · {n["created_at"][11:16]}</div></div>', unsafe_allow_html=True)
