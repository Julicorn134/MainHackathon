"""Blood centre, screen 1: the 14-day outlook, shortage alert, what-if simulator, recommendation."""

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

import forecast as fx
import forecast_data
import store
import ui

@st.cache_data
def get_summary(df: pd.DataFrame) -> pd.DataFrame:
    return fx.summary_table(df)


@st.cache_data
def get_backtest(df: pd.DataFrame) -> dict:
    return {bt: fx.backtest(df, bt) for bt in df.blood_type.unique()}


def ui_request_button(bt: str, rec: dict, open_req: dict | None = None) -> None:
    """The bridge to screen 2: a recommendation nobody can act on is only a report."""
    if rec["risk"] == "Low":
        return
    label = f"Go to the open {bt} request" if open_req else f"Turn into a donor request for {bt}"
    if st.button(label, type="primary", key=f"to_request_{bt}"):
        if not open_req:
            st.session_state["request_prefill"] = {"blood_type": bt, "target": rec["target_units"],
                                                   "window": rec["window"], "days_to_safety": rec["days_to_safety"]}
        st.session_state["_goto"] = "Requests"
        st.rerun()
    if open_req:
        st.caption(f"{open_req['id']} for {bt} is already open. Close it on the Requests page before sending "
                   "another one for this blood type.")


def render(user: dict) -> None:
    source = st.radio("Forecast data", ["uploaded", "demo"],
                      format_func=lambda s: "Uploaded data" if s == "uploaded" else "Synthetic demonstration",
                      horizontal=True, key="forecast_source")
    df = forecast_data.load(user["username"], source)
    quality = forecast_data.quality(df)
    if source == "uploaded":
        st.caption("Fits the model to your saved daily records. Dates are relative to each type's last recorded day. "
                   "Future holidays, unit expiry, transfers and campaign bookings are not included in this baseline.")
    else:
        st.caption("Using the bundled synthetic demonstration, including its configured holiday assumptions.")
    if any(not r["ready"] for r in quality):
        st.warning("Some blood types need more complete history and are excluded from this forecast.")
        st.dataframe(pd.DataFrame(quality), hide_index=True)
    df = forecast_data.ready_data(df)
    if df.empty:
        st.info("No forecast-ready records. Add at least 42 consecutive daily rows for a blood type under Data, "
                "or explicitly choose the synthetic demonstration above.")
        return
    summary = get_summary(df)
    today = df.date.max()
    ranked = summary.assign(o=summary.risk.map(ui.RISK_ORDER)).sort_values(["o", "days_of_supply"])
    worst = ranked.iloc[0]

    at_risk = summary[summary.risk != "Low"]
    critical = summary[summary.risk == "Critical"].sort_values("days_to_safety")
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Units in stock", f"{summary.inventory.sum():,}")
    k2.metric("Blood types at risk (14 days)", f"{len(at_risk)} of {len(summary)}")
    k3.metric("Earliest projected shortage",
              f"{critical.iloc[0].blood_type} in {int(critical.iloc[0].days_to_safety)} days" if len(critical) else "None")
    errors = [v for v in get_backtest(df).values() if v is not None]
    k4.metric("Forecast error (14-day backtest)", f"{np.mean(errors):.1%}" if errors else "Not defined",
              help="Model trained without the last 14 days, then scored on total demand for those days. "
                   "Average across the available types with nonzero held-out demand; not real-world validation.")

    # ------------------------------------------------------------------ status cards
    st.markdown("#### Current stock and 14-day outlook")
    cards = []
    for r in summary.itertuples():
        note = (f"below safety in {int(r.days_to_safety)} days" if r.risk == "Critical"
                else f"projected low: {r.projected_min:,}")
        cards.append(f'<div class="bs-card"><div class="bt">{r.blood_type}</div>'
                     f'<div class="units"><b>{r.inventory:,}</b> units<br>{r.days_of_supply:.1f} days of supply</div>'
                     f'{ui.chip(r.risk)}<div class="sub">{note}</div></div>')
    st.markdown(f'<div class="bs-grid">{"".join(cards)}</div>', unsafe_allow_html=True)

    with st.expander("Table view"):
        st.dataframe(
            summary.assign(risk=summary.risk.map(lambda r: f"{ui.STATUS[r]['icon']} {r}")).rename(columns={
                "blood_type": "Blood type", "inventory": "Inventory", "days_of_supply": "Days of supply",
                "projected_min": "Projected 14-day low", "safety": "Safety threshold",
                "warning": "Warning threshold", "risk": "14-day risk", "days_to_safety": "Days to shortage"}),
            hide_index=True, use_container_width=True,
            column_config={"Days of supply": st.column_config.NumberColumn(format="%.1f")})

    # ------------------------------------------------------------- blood type detail
    st.markdown("")
    available = list(summary.blood_type)
    bt = st.segmented_control("Blood type", available, default=worst.blood_type) or worst.blood_type
    if bt not in available:
        bt = worst.blood_type
    today = df[df.blood_type == bt].date.max()
    st.caption(f"{bt} history through {today:%d %b %Y}. Forecast runs from the following day.")
    safety, warning = fx.thresholds(df, bt)
    base = fx.forecast_type(df, bt)
    rec = fx.recommend(df, bt, base, safety, warning)
    current = int(df[df.blood_type == bt].inventory.iloc[-1])
    open_req = store.open_request(user["org"], bt)
    booked = store.expected_donations(user["org"], bt) if source == "demo" else 0
    booked_fc = fx.apply_campaign(base, booked, fx.CAMPAIGN_LEAD_DAYS + 1, 5) if booked else None

    if rec["risk"] == "Critical":
        st.markdown(
            f'<div class="bs-alert"><h4>⚠️ Potential {bt} shortage detected</h4>'
            f'<p>Last recorded stock: <b>{current:,} units</b>. Projected to be under the safety '
            f'threshold of <b>{safety:,} units</b> in <b>{rec["days_to_safety"]} days</b>, reaching '
            f'<b>{rec["day7_inventory"]:,.0f} units</b> a week from now.</p></div>', unsafe_allow_html=True)
    elif rec["risk"] == "Medium":
        st.markdown(
            f'<div class="bs-alert" style="border-color:#fab219;background:#fdf3d9"><h4>🟡 {bt} supply tightening</h4>'
            f'<p>{current:,} units in stock. Projected to dip under the warning level of {warning:,} '
            f'in {rec["days_to_warning"]} days, while staying above the safety threshold of {safety:,}.</p></div>',
            unsafe_allow_html=True)
    else:
        st.markdown(
            f'<div class="bs-alert ok"><h4>🟢 {bt} supply stable</h4><p>{current:,} units in stock. '
            f'Projected to stay above the warning level of {warning:,} for the next 14 days.</p></div>',
            unsafe_allow_html=True)

    chart_col, side_col = st.columns([2.1, 1], gap="large")

    with side_col:
        st.markdown("##### What-if: donor campaign")
        default_units = min(rec["target_units"], 300)
        extra = st.slider("Additional donations", 0, 300, 0, 10, key=f"extra_{bt}",
                          help=f"Model suggestion for {bt}: {default_units}")
        delay = st.slider("Launch campaign in (days)", 0, 7, 0, key=f"delay_{bt}")
        window = st.slider("Campaign length (days)", 3, 10, 5, key=f"window_{bt}")
        st.caption(f"Units become usable {fx.CAMPAIGN_LEAD_DAYS} days after launch "
                   "(outreach ramp-up, then testing and processing).")

    scenario = fx.apply_campaign(base, extra, delay + fx.CAMPAIGN_LEAD_DAYS + 1, window)
    after = fx.assess(scenario, safety, warning)

    with chart_col:
        hist = df[df.blood_type == bt].tail(30)
        # Forecast traces start at today's actual so the line is continuous.
        anchor = pd.DataFrame({"date": [today], "inventory": [current], "low": [current], "high": [current]})
        b = pd.concat([anchor, base[["date", "inventory", "low", "high"]]])
        s = pd.concat([anchor, scenario[["date", "inventory", "low", "high"]]])

        fig = go.Figure()
        fig.add_trace(go.Scatter(x=b.date, y=b.high, mode="lines", line=dict(width=0), hoverinfo="skip", showlegend=False))
        fig.add_trace(go.Scatter(x=b.date, y=b.low, mode="lines", line=dict(width=0), fill="tonexty",
                                 fillcolor="rgba(42,120,214,0.12)", name="Heuristic range", hoverinfo="skip"))
        fig.add_trace(go.Scatter(x=hist.date, y=hist.inventory, mode="lines", name="Actual inventory",
                                 line=dict(color=ui.BLUE, width=2), hovertemplate="%{y:,.0f} units"))
        fig.add_trace(go.Scatter(x=b.date, y=b.inventory, mode="lines", name="Forecast, no action",
                                 line=dict(color=ui.BLUE, width=2, dash="dash"), hovertemplate="%{y:,.0f} units"))
        if booked_fc is not None:
            bk = pd.concat([anchor, booked_fc[["date", "inventory", "low", "high"]]])
            fig.add_trace(go.Scatter(x=bk.date, y=bk.inventory, mode="lines",
                                     name=f"Forecast, with {booked:,} booked donations",
                                     line=dict(color=ui.AQUA, width=2, dash="dot"), hovertemplate="%{y:,.0f} units"))
        if extra > 0:
            fig.add_trace(go.Scatter(x=s.date, y=s.inventory, mode="lines", name=f"Forecast, +{extra} donations",
                                     line=dict(color=ui.AQUA, width=2.5), hovertemplate="%{y:,.0f} units"))

        x0, x1 = hist.date.min(), base.date.max()
        for level, label, color in ((warning, "Warning", "#fab219"), (safety, "Safety threshold", "#d03b3b")):
            fig.add_shape(type="line", x0=x0, x1=x1, y0=level, y1=level, line=dict(color=color, width=1.5, dash="dot"))
            fig.add_annotation(x=x0, y=level, text=f"{label} · {level:,}", showarrow=False, xanchor="left",
                               yanchor="bottom", font=dict(size=11, color=ui.INK_2))
        fig.add_shape(type="line", x0=today, x1=today, yref="paper", y0=0, y1=1, line=dict(color=ui.AXIS, width=1))
        fig.add_annotation(x=today, yref="paper", y=1.0, text="Today", showarrow=False, xanchor="right",
                           yanchor="top", xshift=-4, font=dict(size=11, color=ui.MUTED))
        if rec["days_to_safety"]:
            hit = base.iloc[rec["days_to_safety"] - 1]
            fig.add_trace(go.Scatter(x=[hit.date], y=[hit.inventory], mode="markers", showlegend=False, hoverinfo="skip",
                                     marker=dict(size=10, color="#d03b3b", line=dict(color="#fff", width=2))))
            fig.add_annotation(x=hit.date, y=hit.inventory, text=f"Below safety in {rec['days_to_safety']} days",
                               showarrow=True, arrowhead=0, arrowcolor=ui.MUTED, ax=40, ay=-34,
                               font=dict(size=12, color=ui.INK))

        ymax = max(hist.inventory.max(), b.high.max(), s.inventory.max(), warning,
                   booked_fc.inventory.max() if booked_fc is not None else 0) * 1.12
        # The title lives in the page, not in the figure: with four traces the legend wraps to two rows
        # and a Plotly title in the same top margin collides with it.
        st.markdown(f"##### {bt} inventory: last 30 days and 14-day projection")
        fig.update_layout(
            height=430, margin=dict(l=10, r=10, t=76, b=10), hovermode="x unified",
            plot_bgcolor="#fcfcfb", paper_bgcolor="#fcfcfb", font=dict(color=ui.INK_2),
            legend=dict(orientation="h", yanchor="bottom", y=1.0, xanchor="right", x=1),
            yaxis=dict(title="Units", range=[0, ymax], gridcolor=ui.GRID, zeroline=False),
            xaxis=dict(showgrid=False, linecolor=ui.AXIS, tickformat="%d %b"))
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

    with side_col:
        before_txt = (f"shortage in {rec['days_to_safety']} days" if rec["risk"] == "Critical"
                      else "under warning level" if rec["risk"] == "Medium" else "stable")
        st.markdown(f"**Without campaign:** {ui.chip(rec['risk'])} {before_txt}", unsafe_allow_html=True)
        if extra > 0:
            after_txt = {
                "Critical": f"still short in {after['days_to_safety']} days: too little or too late",
                "Medium": "shortage avoided, buffer still thin on day 14",
                "Low": "shortage avoided, stock back above the warning level",
            }[after["outcome"]]
            st.markdown(f"**With +{extra} donations:** {ui.chip(after['outcome'])} {after_txt}", unsafe_allow_html=True)
            st.caption(f"Projected 14-day low: {rec['min_inventory']:,.0f} → {after['min_inventory']:,.0f} units")
        else:
            st.caption("Move the slider to test an intervention.")

    # ---------------------------------------------------------------- recommendation
    st.markdown("#### 🤖 BloodSight recommendation")
    rec_col, why_col = st.columns([1.2, 1], gap="large")
    with rec_col:
        if rec["risk"] == "Low":
            st.markdown(f'<div class="bs-rec"><b>No intervention needed for {bt}.</b><br>'
                        'Keep routine collection schedules. BloodSight re-evaluates the outlook daily.</div>',
                        unsafe_allow_html=True)
        else:
            lw = rec["launch_within_days"]
            launch = "today" if lw == 0 else f"within {lw * 24} hours" if lw <= 3 else f"within {lw} days"
            headline = (f"Launch a targeted {bt} donor campaign {launch}, before stock reaches critical levels."
                        if rec["risk"] == "Critical"
                        else f"Schedule a modest {bt} donor drive {launch} to rebuild the buffer.")
            st.markdown(
                f'<div class="bs-rec"><b>{headline}</b><table>'
                f'<tr><td>Target</td><td>{rec["target_units"]} additional donations</td></tr>'
                f'<tr><td>Campaign window</td><td>{rec["window"]} days</td></tr>'
                f'<tr><td>Latest effective launch</td><td>{launch}</td></tr>'
                f'<tr><td>Priority</td><td>{rec["priority"]}</td></tr>'
                f'<tr><td>Expected 14-day risk after campaign</td><td>{ui.chip(rec["risk_after"])}</td></tr></table></div>',
                unsafe_allow_html=True)
        if booked:
            after_booked = fx.assess(booked_fc, safety, warning)
            # One request per blood type can be open. A closed one keeps its appointments, so it still counts.
            one = (f"{open_req['id']}, the open {bt} request of this centre" if open_req
                   else f"closed {bt} requests of this centre, whose appointments stand")
            st.markdown(f"**{booked:,} donation{'s' if booked != 1 else ''} "
                        f"{'are' if booked != 1 else 'is'} already booked** through {one}. "
                        f"{'They are' if booked != 1 else 'It is'} in the chart as a dotted line. "
                        f"Projected 14-day low with {'them' if booked != 1 else 'it'}: "
                        f"{after_booked['min_inventory']:,.0f} units.")
        elif open_req:
            st.markdown(f"**{open_req['id']} for {bt} is open** and nobody has booked a slot yet, so the projection "
                        "above is the one without donations. Bookings appear here as they come in.")
        else:
            st.caption(f"No {bt} request of this centre has bookings, so no booked donations are in the projection.")
        ui_request_button(bt, rec, open_req)
    with why_col:
        st.markdown("**Why the model sees this**")
        for d in rec["drivers"]:
            st.markdown(f"- {d}")

    with st.expander("Behind the forecast: daily usage and donations"):
        h = df[df.blood_type == bt].tail(30)
        flow = go.Figure()
        for col, name, color in (("demand", "Usage", "#eb6834"), ("donations", "Donations", ui.BLUE)):
            flow.add_trace(go.Scatter(x=h.date, y=h[col], mode="lines", name=name, legendgroup=name,
                                      line=dict(color=color, width=2), hovertemplate="%{y:,.0f}"))
            flow.add_trace(go.Scatter(x=base.date, y=base[col], mode="lines", name=f"{name} forecast", legendgroup=name,
                                      line=dict(color=color, width=2, dash="dash"), hovertemplate="%{y:,.0f}"))
        flow.update_layout(height=320, margin=dict(l=10, r=10, t=40, b=10), hovermode="x unified",
                           plot_bgcolor="#fcfcfb", paper_bgcolor="#fcfcfb", font=dict(color=ui.INK_2),
                           legend=dict(orientation="h", yanchor="bottom", y=1.0, xanchor="right", x=1),
                           yaxis=dict(title="Units per day", rangemode="tozero", gridcolor=ui.GRID, zeroline=False),
                           xaxis=dict(showgrid=False, linecolor=ui.AXIS, tickformat="%d %b"))
        st.plotly_chart(flow, use_container_width=True, config={"displayModeBar": False})
        error = get_backtest(df)[bt]
        error_label = f"{error:.1%}" if error is not None else "undefined (zero held-out demand)"
        st.markdown(
            f"**Model.** One ridge regression per blood type and per flow (usage, donations), trained on the last "
            f"{fx.TRAIN_DAYS} days with day-of-week, trend and public-holiday features. Projected inventory = current "
            f"inventory + predicted donations − predicted usage. Risk: projected stock under {fx.SAFETY_DAYS} days of "
            f"supply is critical, under {fx.WARNING_DAYS} days is medium. 14-day backtest error for {bt}: "
            f"{error_label}. The backtest hides the most recent 14 days, so a type whose trend changed inside "
            "that window scores worse than a stable one.")

    st.caption("Prototype on synthetic data. Decision support for collection planning, not for clinical decisions.")
