import streamlit as st
import pandas as pd
import plotly.express as px

from core.engine import (
    init_state, inject_styles, APP_NAME, get_report_title,
    std_cols, guess_status_column,
)

st.set_page_config(page_title="Dashboard – Smart WSR", page_icon="📊", layout="wide")
init_state()
inject_styles()

st.markdown(
    """
    <div class='app-header'>
        <div>
            <h1>📊 Dashboard</h1>
            <p class='subtitle'>Dynamic report sections — configured on the Home page.</p>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

report = st.session_state.get("report")

if report is None:
    st.warning("No report loaded. Go to **🏠 Home**, upload a file and click **🚀 Generate Report**.")
    st.stop()

# ── Report title ──────────────────────────────────────────────
st.markdown(
    f"""
    <div class='report-card'>
        <div class='report-label'>ACTIVE REPORT</div>
        <h2>{get_report_title(report)}</h2>
        <p class='subtitle'>
            {len(st.session_state.working_df)} rows &nbsp;·&nbsp;
            {len(report.get('filter_criteria') or {})} active filter(s)
        </p>
    </div>
    """,
    unsafe_allow_html=True,
)

# ── Active filters banner ─────────────────────────────────────
criteria = report.get("filter_criteria") or {}
active = [f"**{k}:** {v}" for k, v in criteria.items() if v]
if active:
    st.markdown(
        """<div class='section-card'><h3>Active Filters</h3></div>""",
        unsafe_allow_html=True,
    )
    st.markdown("  ".join([f"• {a}" for a in active]))


# ══════════════════════════════════════════════════════════════
# DYNAMIC SECTIONS (config-driven)
# ══════════════════════════════════════════════════════════════
def _render_section(section: dict, idx: int):
    title = section.get("title", f"Section {idx + 1}")
    stype = section.get("type", "table")
    data = section.get("data")

    st.markdown(
        f"""
        <div class='section-card'>
            <h3>{idx + 1}. {title}</h3>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # ── TABLE ─────────────────────────────────────────────────
    if stype == "table":
        if isinstance(data, pd.DataFrame) and not data.empty:
            st.dataframe(data, width="stretch", hide_index=True)
        else:
            st.info("No data to display for this section.")

    # ── PIVOT TABLE ───────────────────────────────────────────
    elif stype == "pivot":
        if isinstance(data, pd.DataFrame) and not data.empty:
            st.dataframe(data, width="stretch", hide_index=True)
        else:
            st.info("Configure a Group By column for this section.")

    # ── BAR CHART ─────────────────────────────────────────────
    elif stype == "bar_chart":
        if isinstance(data, pd.DataFrame) and not data.empty and len(data.columns) >= 2:
            x_col, y_col = data.columns[0], data.columns[1]
            fig = px.bar(
                data, x=x_col, y=y_col,
                title=title,
                color=x_col,
                color_discrete_sequence=px.colors.qualitative.Plotly,
                labels={y_col: y_col, x_col: x_col},
            )
            fig.update_layout(
                height=380,
                plot_bgcolor="#ffffff",
                paper_bgcolor="#ffffff",
                font=dict(family="Inter, sans-serif", size=13),
                xaxis_tickangle=-35,
                margin=dict(b=100, t=40),
                showlegend=False,
            )
            fig.update_traces(marker_line_width=0)
            st.plotly_chart(fig, width="stretch", key=f"bar_{section['id']}")
        else:
            st.info("Configure a Group By column for this bar chart.")

    # ── PIE CHART ─────────────────────────────────────────────
    elif stype == "pie_chart":
        if isinstance(data, pd.DataFrame) and not data.empty and len(data.columns) >= 2:
            names_col, values_col = data.columns[0], data.columns[1]
            fig = px.pie(
                data,
                names=names_col,
                values=values_col,
                title=title,
                color_discrete_sequence=px.colors.qualitative.Set2,
                hole=0.35,
            )
            fig.update_layout(
                height=380,
                plot_bgcolor="#ffffff",
                paper_bgcolor="#ffffff",
                font=dict(family="Inter, sans-serif", size=13),
                margin=dict(t=40, b=20),
            )
            fig.update_traces(textposition="inside", textinfo="percent+label")
            st.plotly_chart(fig, width="stretch", key=f"pie_{section['id']}")
        else:
            st.info("Configure a Group By column for this pie chart.")

    # ── KPI CARDS ─────────────────────────────────────────────
    elif stype == "kpi_cards":
        if isinstance(data, dict) and data:
            items = list(data.items())
            n_cols = min(len(items), 4)
            metric_cols = st.columns(n_cols)
            for i, (name, val) in enumerate(items):
                metric_cols[i % n_cols].metric(name, f"{val:,}" if isinstance(val, (int, float)) else val)
        else:
            st.info("No metric data for this section.")


sections = report.get("sections")

if sections:
    # ── Config-driven rendering — respects layout (vertical / horizontal) ──
    idx = 0
    display_num = 0  # sequential display number shown in section header
    while idx < len(sections):
        sec = sections[idx]
        layout = sec.get("layout", "vertical")
        next_sec = sections[idx + 1] if idx + 1 < len(sections) else None
        next_layout = next_sec.get("layout", "vertical") if next_sec else "vertical"

        if layout == "horizontal" and next_sec and next_layout == "horizontal":
            # Render two horizontal sections side-by-side
            col_left, col_right = st.columns(2)
            with col_left:
                _render_section(sec, display_num)
            with col_right:
                _render_section(next_sec, display_num + 1)
            idx += 2
            display_num += 2
        else:
            _render_section(sec, display_num)
            idx += 1
            display_num += 1
else:
    # ── Legacy / Auto-report rendering ───────────────────────
    st.info("This report uses the legacy auto-mode. Re-generate with **Custom** mode for dynamic sections.", icon="ℹ️")

    # 1. Project Status
    st.markdown("""<div class='section-card'><h3>1. Project Status</h3></div>""", unsafe_allow_html=True)
    st.dataframe(report["summary"], width="stretch", hide_index=True)

    # 2. Project Aging Summary
    st.markdown("""<div class='section-card'><h3>2. Project Aging Summary</h3></div>""", unsafe_allow_html=True)
    st.dataframe(report["aging"], width="stretch")

    # 3. Delivery Highlights
    st.markdown("""<div class='section-card'><h3>3. Delivery Highlights</h3></div>""", unsafe_allow_html=True)
    if len(report["delivery"]) == 0:
        st.info("No delivery in the selected week.")
    else:
        st.dataframe(report["delivery"], width="stretch", hide_index=True)

    # 4. Risks / Aging Projects
    st.markdown("""<div class='section-card'><h3>4. Risks / Aging Projects</h3></div>""", unsafe_allow_html=True)
    st.dataframe(report["risks"], width="stretch", hide_index=True)

    # 5. Outlook
    st.markdown("""<div class='section-card'><h3>5. Outlook for Next Week</h3></div>""", unsafe_allow_html=True)
    if len(report["outlook"]) == 0:
        st.info("No deliveries scheduled for next week.")
    else:
        st.dataframe(report["outlook"], width="stretch", hide_index=True)

    # 6. Status Charts
    st.markdown("""<div class='section-card'><h3>6. Status Dashboard</h3></div>""", unsafe_allow_html=True)
    ch1, ch2 = st.columns(2)
    with ch1:
        try:
            working_df = report["working"].copy()
            cols = std_cols(working_df)
            status_col = cols.get("status") or guess_status_column(working_df)
            if status_col and status_col in working_df.columns:
                status_counts = (
                    working_df[status_col].astype(str).str.lower()
                    .value_counts().reset_index()
                )
                status_counts.columns = ["Status", "Count"]
                fig = px.bar(
                    status_counts, x="Status", y="Count",
                    title="Project Status Distribution",
                    color="Status",
                    color_discrete_sequence=px.colors.qualitative.Plotly,
                )
                fig.update_layout(
                    height=400, showlegend=False,
                    xaxis_tickangle=-45, margin=dict(b=150),
                    plot_bgcolor="#ffffff", paper_bgcolor="#ffffff",
                )
                st.plotly_chart(fig, width="stretch", key="dash_status_bar")
        except Exception as e:
            st.error(f"Status chart error: {e}")
    with ch2:
        try:
            aging_df = report["aging"].reset_index()
            aging_cols = ["0 - 30 Days", "30 - 60 Days", "60 - 90 Days", "> 90 Days"]
            aging_data = [{"Bucket": c, "Count": int(aging_df[c].sum())} for c in aging_cols if c in aging_df.columns]
            aging_data = [d for d in aging_data if d["Count"] > 0]
            if aging_data:
                fig_pie = px.pie(
                    pd.DataFrame(aging_data), names="Bucket", values="Count",
                    title="Project Aging Distribution",
                    color_discrete_sequence=px.colors.qualitative.Set3,
                    hole=0.35,
                )
                fig_pie.update_layout(
                    height=400,
                    plot_bgcolor="#ffffff", paper_bgcolor="#ffffff",
                )
                st.plotly_chart(fig_pie, width="stretch", key="dash_aging_pie")
        except Exception as e:
            st.error(f"Aging chart error: {e}")

    # 7. Executive Summary
    st.markdown("""<div class='section-card'><h3>7. Executive Summary</h3></div>""", unsafe_allow_html=True)
    for b in report["bullets"]:
        html = (
            f'<div style="display:flex;border:1px solid #e0e4ed;background:#f8fafc;'
            f'margin-bottom:12px;border-radius:8px;overflow:hidden;'
            f'box-shadow:0 2px 8px rgba(10,10,30,0.04);">'
            f'<div style="width:6px;background:#1a3a8c;flex-shrink:0;"></div>'
            f'<div style="padding:14px 16px;font-size:0.93rem;line-height:1.7;color:#1a1a2e;">• {b}</div></div>'
        )
        st.markdown(html, unsafe_allow_html=True)

# ── Project details (from chat) ───────────────────────────────
if st.session_state.get("project_details"):
    st.markdown("""<div class='section-card'><h3>Project Details</h3></div>""", unsafe_allow_html=True)
    st.markdown(st.session_state.project_details, unsafe_allow_html=True)
