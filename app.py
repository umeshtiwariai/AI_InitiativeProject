import uuid
import streamlit as st
import pandas as pd

from core.engine import (
    APP_NAME, init_state, inject_styles, add_chat, reset_all,
    load_file, build_report, build_report_from_config,
    validate_uploaded_data, display_validation_results,
    detect_col_config, default_section_configs, apply_filter_rules,
)

st.set_page_config(page_title="Smart WSR Agent", page_icon="📊", layout="wide")
init_state()
inject_styles()

# ── Sidebar ───────────────────────────────────────────────────
with st.sidebar:

    # ── Brand header ──────────────────────────────────────────
    st.markdown(
        """
        <div class='sb-brand'>
            <div class='sb-brand-title'>📊 Smart WSR</div>
            <div class='sb-brand-sub'>AI-Powered Weekly Status Reporting</div>
            <span class='sb-brand-badge'>BusinessNext Enterprise</span>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # ── Session status ────────────────────────────────────────
    st.markdown("<div class='sb-label'>Session Status</div>", unsafe_allow_html=True)

    src_df = st.session_state.get("source_df")
    rpt    = st.session_state.get("report")

    if src_df is not None:
        st.markdown(
            f"""<div class='sb-status success'>
                <div class='sb-status-icon'>✅</div>
                <div class='sb-status-text'>
                    <div class='sb-status-main'>{len(src_df):,} rows loaded</div>
                    <div class='sb-status-sub'>{len(src_df.columns)} columns detected</div>
                </div>
            </div>""",
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            """<div class='sb-status idle'>
                <div class='sb-status-icon'>📂</div>
                <div class='sb-status-text'>
                    <div class='sb-status-main'>No data loaded</div>
                    <div class='sb-status-sub'>Upload a file to begin</div>
                </div>
            </div>""",
            unsafe_allow_html=True,
        )

    if rpt is not None:
        n_sec = len(rpt.get("sections") or [])
        mode  = f"Custom · {n_sec} sections" if n_sec else "Auto (standard)"
        n_flt = len(st.session_state.get("filter_rules") or [])
        flt_txt = f"{n_flt} filter(s) active" if n_flt else "No filters"
        st.markdown(
            f"""<div class='sb-status info'>
                <div class='sb-status-icon'>📊</div>
                <div class='sb-status-text'>
                    <div class='sb-status-main'>Report active</div>
                    <div class='sb-status-sub'>{mode} &nbsp;·&nbsp; {flt_txt}</div>
                </div>
            </div>""",
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            """<div class='sb-status idle'>
                <div class='sb-status-icon'>🗒️</div>
                <div class='sb-status-text'>
                    <div class='sb-status-main'>No report generated</div>
                    <div class='sb-status-sub'>Generate to enable Dashboard & Export</div>
                </div>
            </div>""",
            unsafe_allow_html=True,
        )

    # ── Navigation ────────────────────────────────────────────
    st.markdown("<hr class='sb-divider'>", unsafe_allow_html=True)
    st.markdown("<div class='sb-label'>Navigation</div>", unsafe_allow_html=True)

    nav_pages = [
        ("🏠", "Home",           "Upload data & generate reports"),
        ("📊", "Dashboard",      "View report sections & charts"),
        ("🤖", "AI Chat",        "Ask questions about your data"),
        ("🔍", "Project Search", "Search & filter project records"),
        ("📥", "Export",         "Download PDF / PPT / Excel or email"),
        ("⚙️", "Settings",       "SMTP, week mode & preferences"),
    ]
    for icon, name, desc in nav_pages:
        st.markdown(
            f"""<div class='sb-nav-card'>
                <div class='sb-nav-card-title'>{icon} {name}</div>
                <div class='sb-nav-card-desc'>{desc}</div>
            </div>""",
            unsafe_allow_html=True,
        )

    # ── Help & Guidance ───────────────────────────────────────
    st.markdown("<hr class='sb-divider'>", unsafe_allow_html=True)
    st.markdown("<div class='sb-label'>Help &amp; Guidance</div>", unsafe_allow_html=True)

    with st.expander("🚀 Getting Started", expanded=False):
        st.markdown(
            """
            <div class='sb-step'>
                <div class='sb-step-num'>1</div>
                <div class='sb-step-body'>
                    <div class='sb-step-title'>Upload your data</div>
                    <div class='sb-step-desc'>Use <b>Upload Local File</b> to load an Excel (.xlsx/.xls) or CSV file. Supports up to thousands of rows.</div>
                </div>
            </div>
            <div class='sb-step'>
                <div class='sb-step-num'>2</div>
                <div class='sb-step-body'>
                    <div class='sb-step-title'>Generate a report</div>
                    <div class='sb-step-desc'>Click <b>Generate Initial Report</b> for the standard auto-report, or switch to the <b>Custom Builder</b> tab for full control.</div>
                </div>
            </div>
            <div class='sb-step'>
                <div class='sb-step-num'>3</div>
                <div class='sb-step-body'>
                    <div class='sb-step-title'>Explore the Dashboard</div>
                    <div class='sb-step-desc'>Navigate to 📊 <b>Dashboard</b> to view all sections, charts, and KPI cards.</div>
                </div>
            </div>
            <div class='sb-step'>
                <div class='sb-step-num'>4</div>
                <div class='sb-step-body'>
                    <div class='sb-step-title'>Export or share</div>
                    <div class='sb-step-desc'>Go to 📥 <b>Export</b> to download as PDF, PPT, Image, or Excel — or email directly to stakeholders.</div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with st.expander("🔧 Custom Report Builder", expanded=False):
        st.markdown(
            """
            <div class='sb-step'>
                <div class='sb-step-num'>1</div>
                <div class='sb-step-body'>
                    <div class='sb-step-title'>Assign Column Roles</div>
                    <div class='sb-step-desc'><b>Step 1</b> — Tell the builder which columns are Project Name, Status, Dates, and Metrics. Auto-detected on load.</div>
                </div>
            </div>
            <div class='sb-step'>
                <div class='sb-step-num'>2</div>
                <div class='sb-step-body'>
                    <div class='sb-step-title'>Configure Sections</div>
                    <div class='sb-step-desc'><b>Step 2</b> — Add, edit, or remove sections. Choose type: Table, Pivot, Bar Chart, Pie Chart, or KPI Cards. Set <b>Horizontal</b> layout to display two sections side-by-side.</div>
                </div>
            </div>
            <div class='sb-step'>
                <div class='sb-step-num'>3</div>
                <div class='sb-step-body'>
                    <div class='sb-step-title'>Add Filter Rules</div>
                    <div class='sb-step-desc'><b>Step 3</b> — Filter rows by any column using Contains, Equals, In List, &gt;/&lt; comparisons, and more. Chain rules with AND / OR. A live row count shows the impact.</div>
                </div>
            </div>
            <div class='sb-step'>
                <div class='sb-step-num'>4</div>
                <div class='sb-step-body'>
                    <div class='sb-step-title'>Preview &amp; Generate</div>
                    <div class='sb-step-desc'>Toggle <b>👁️ Preview</b> on any section for an inline data preview before generating. Click <b>🚀 Generate Custom Report</b> to push it to the Dashboard.</div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with st.expander("🤖 AI Chat Agent", expanded=False):
        st.markdown(
            """
            <div class='sb-step'>
                <div class='sb-step-num'>💬</div>
                <div class='sb-step-body'>
                    <div class='sb-step-title'>Ask in natural language</div>
                    <div class='sb-step-desc'>Type questions like <i>"Show UAT projects"</i>, <i>"Top 5 by aging"</i>, or <i>"Projects going live next week"</i>.</div>
                </div>
            </div>
            <div class='sb-step'>
                <div class='sb-step-num'>🔍</div>
                <div class='sb-step-body'>
                    <div class='sb-step-title'>Smart filtering</div>
                    <div class='sb-step-desc'>The agent detects status keywords, numeric thresholds, and date context to filter your data automatically.</div>
                </div>
            </div>
            <div class='sb-step'>
                <div class='sb-step-num'>📊</div>
                <div class='sb-step-body'>
                    <div class='sb-step-title'>Summaries &amp; insights</div>
                    <div class='sb-step-desc'>Ask for executive summaries, risk highlights, or delivery forecasts — powered by Gemini AI.</div>
                </div>
            </div>
            <div class='sb-tip'><strong>Tip:</strong> The AI works on your loaded data, so upload a file first before chatting.</div>
            """,
            unsafe_allow_html=True,
        )

    with st.expander("🔍 Project Search", expanded=False):
        st.markdown(
            """
            <div class='sb-step'>
                <div class='sb-step-num'>🔎</div>
                <div class='sb-step-body'>
                    <div class='sb-step-title'>Full-text search</div>
                    <div class='sb-step-desc'>Search across all text columns simultaneously. Results update instantly as you type.</div>
                </div>
            </div>
            <div class='sb-step'>
                <div class='sb-step-num'>⚙️</div>
                <div class='sb-step-body'>
                    <div class='sb-step-title'>Column filters</div>
                    <div class='sb-step-desc'>Filter by Status, date ranges, aging buckets, and more using dedicated dropdowns and sliders.</div>
                </div>
            </div>
            <div class='sb-tip'><strong>Tip:</strong> Combine search + column filters to drill into a specific project set, then export just that subset.</div>
            """,
            unsafe_allow_html=True,
        )

    with st.expander("📥 Export & Email", expanded=False):
        st.markdown(
            """
            <div class='sb-step'>
                <div class='sb-step-num'>📄</div>
                <div class='sb-step-body'>
                    <div class='sb-step-title'>PDF Report</div>
                    <div class='sb-step-desc'>Generates a formatted multi-page PDF with all report sections, ready for stakeholder distribution.</div>
                </div>
            </div>
            <div class='sb-step'>
                <div class='sb-step-num'>📑</div>
                <div class='sb-step-body'>
                    <div class='sb-step-title'>PowerPoint</div>
                    <div class='sb-step-desc'>Creates a branded .pptx slide deck — one slide per section, with charts and tables.</div>
                </div>
            </div>
            <div class='sb-step'>
                <div class='sb-step-num'>📊</div>
                <div class='sb-step-body'>
                    <div class='sb-step-title'>Excel Workbook</div>
                    <div class='sb-step-desc'>Exports all report data into a formatted .xlsx file with separate sheets per section.</div>
                </div>
            </div>
            <div class='sb-step'>
                <div class='sb-step-num'>📧</div>
                <div class='sb-step-body'>
                    <div class='sb-step-title'>Email delivery</div>
                    <div class='sb-step-desc'>Configure SMTP on the ⚙️ Settings page, then send the report image and Excel to any recipients — comma or semicolon separated.</div>
                </div>
            </div>
            <div class='sb-tip'><strong>Tip:</strong> Generate the report first; the Export page uses the currently active report.</div>
            """,
            unsafe_allow_html=True,
        )

    with st.expander("💡 Tips & Shortcuts", expanded=False):
        st.markdown(
            """
            <div class='sb-tip' style='margin-top:0;'>
                <strong>Portal tab:</strong> Use <em>Open External Portal</em> to quickly reach SharePoint, Google Sheets, OneDrive, or any custom URL — then upload the downloaded file.
            </div>
            <div class='sb-tip'>
                <strong>Week mode:</strong> Switch between <em>Last week</em> and <em>Current week</em> in the Custom Builder or Settings to change the reporting window.
            </div>
            <div class='sb-tip'>
                <strong>Section preview:</strong> Toggle <em>👁️ Preview</em> inside a section expander to verify data before generating the full report.
            </div>
            <div class='sb-tip'>
                <strong>Horizontal layout:</strong> Set two adjacent sections to <em>Horizontal</em> layout and they will appear side-by-side on the Dashboard.
            </div>
            <div class='sb-tip'>
                <strong>Filter carry-through:</strong> Filter rules applied in the Custom Builder flow through to all sections and exports automatically.
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown("<hr class='sb-divider'>", unsafe_allow_html=True)
    st.markdown(
        "<div style='font-size:0.7rem;color:#3a4060;text-align:center;padding-bottom:8px;'>"
        "Smart WSR &nbsp;·&nbsp; BusinessNext &nbsp;·&nbsp; v2.0"
        "</div>",
        unsafe_allow_html=True,
    )

# ── Header ─────────────────────────────────────────────────────
st.markdown(
    f"""
    <div class='app-header'>
        <div>
            <h1>📊 {APP_NAME}</h1>
            <p class='subtitle'>Modern weekly status reporting powered by the Smart WSR Agent.</p>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

# ══════════════════════════════════════════════════════════════
# TABS
# ══════════════════════════════════════════════════════════════
tab_upload, tab_portal, tab_custom = st.tabs([
    "📂 Upload Local File",
    "🌐 Open External Portal",
    "🔧 Custom Report Builder",
])

# ──────────────────────────────────────────────────────────────
# TAB 1 — UPLOAD LOCAL FILE  (original, unchanged)
# ──────────────────────────────────────────────────────────────
with tab_upload:
    st.markdown(
        """
        <div class='section-card'>
            <h3>Upload Source Data</h3>
            <div class='section-note'>Upload your project status Excel or CSV file from your computer.</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    file = st.file_uploader(
        "Upload Excel / CSV Source File",
        type=["xlsx", "xls", "csv"],
        help="Supports .csv, .xls, .xlsx formats.",
    )

    if file is not None:
        try:
            preview_df = load_file(file)
            if preview_df is not None and len(preview_df) > 0:
                st.info(
                    f"File: **{file.name}** — **{len(preview_df)} rows** × **{len(preview_df.columns)} columns**"
                )
                validation_results = validate_uploaded_data(preview_df)
                display_validation_results(validation_results)
                with st.expander("Preview first 5 rows", expanded=False):
                    st.dataframe(preview_df.head(5), width="stretch")
        except Exception:
            st.warning("Unable to preview the uploaded file automatically.")

    col_gen, col_rst = st.columns(2)
    with col_gen:
        if st.button("Generate Initial Report", key="gen_upload", width="stretch", type="primary"):
            if file is None:
                st.error("Please upload an Excel or CSV file before generating the report.")
            else:
                try:
                    df = load_file(file)
                    if df is None or len(df) == 0:
                        st.error("The uploaded file is empty or invalid.")
                    else:
                        st.session_state.source_df = df
                        st.session_state.working_df = df.copy()
                        rpt = build_report(df, week_mode=st.session_state.get("week_mode", "last"))
                        st.session_state.report = rpt
                        st.session_state.awaiting_next_action = True
                        add_chat("assistant", "Initial report generated from uploaded file. Navigate to 📊 Dashboard.")
                        st.success("✅ Report generated! Go to **📊 Dashboard** to view it.")
                except Exception as e:
                    st.error(f"Error loading file: {e}")
    with col_rst:
        if st.button("Reset All", key="rst_upload", width="stretch"):
            reset_all()
            st.rerun()

# ──────────────────────────────────────────────────────────────
# TAB 2 — OPEN EXTERNAL PORTAL  (original, unchanged)
# ──────────────────────────────────────────────────────────────
with tab_portal:
    st.markdown(
        """
        <div class='section-card'>
            <h3>Open External Portal</h3>
            <div class='section-note'>
                Open your organisation's web portal in a new tab, download your project data file,
                then upload it below to generate the report.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Quick-access portal buttons
    st.markdown("#### Quick Access — Common Portals")
    qc1, qc2, qc3, qc4 = st.columns(4)
    with qc1:
        st.link_button("🏢 SharePoint", "https://www.sharepoint.com", width="stretch")
    with qc2:
        st.link_button("📊 Google Sheets", "https://sheets.google.com", width="stretch")
    with qc3:
        st.link_button("☁️ OneDrive", "https://onedrive.live.com", width="stretch")
    with qc4:
        st.link_button("📋 Confluence", "https://www.atlassian.com/software/confluence", width="stretch")

    st.divider()

    # Custom portal URL
    st.markdown("#### Custom Portal URL")
    custom_portal_url = st.text_input(
        "Enter your portal URL",
        placeholder="https://your-company-portal.com/reports",
        help="Paste the URL of your internal or external data portal.",
        key="custom_portal_url_input",
    )
    if custom_portal_url.strip():
        st.link_button("🌐 Open Portal in New Tab", custom_portal_url.strip(), width="stretch", type="primary")
    else:
        st.button("🌐 Open Portal in New Tab", disabled=True, width="stretch")

    st.divider()

    # Upload after downloading from portal
    st.markdown("#### Upload File Downloaded from Portal")
    st.info("After downloading your file from the portal above, upload it here.", icon="⬇️")

    portal_file = st.file_uploader(
        "Upload file downloaded from portal",
        type=["xlsx", "xls", "csv"],
        help="Supports .csv, .xls, .xlsx formats.",
        key="portal_file_uploader",
    )

    if portal_file is not None:
        try:
            preview_df = load_file(portal_file)
            if preview_df is not None and len(preview_df) > 0:
                st.info(
                    f"File: **{portal_file.name}** — **{len(preview_df)} rows** × **{len(preview_df.columns)} columns**"
                )
                validation_results = validate_uploaded_data(preview_df)
                display_validation_results(validation_results)
                with st.expander("Preview first 5 rows", expanded=False):
                    st.dataframe(preview_df.head(5), width="stretch")
        except Exception:
            st.warning("Unable to preview the uploaded file automatically.")

    col_gen2, col_rst2 = st.columns(2)
    with col_gen2:
        if st.button("Generate Initial Report", key="gen_portal", width="stretch", type="primary"):
            if portal_file is None:
                st.error("Please upload a file downloaded from the portal.")
            else:
                try:
                    df = load_file(portal_file)
                    if df is None or len(df) == 0:
                        st.error("The uploaded file is empty or invalid.")
                    else:
                        st.session_state.source_df = df
                        st.session_state.working_df = df.copy()
                        st.session_state["last_portal_filename"] = portal_file.name
                        rpt = build_report(df, week_mode=st.session_state.get("week_mode", "last"))
                        st.session_state.report = rpt
                        st.session_state.awaiting_next_action = True
                        add_chat("assistant", f"Report generated from portal file '{portal_file.name}'. Navigate to 📊 Dashboard.")
                        st.success("✅ Report generated! Go to **📊 Dashboard** to view it.")
                except Exception as e:
                    st.error(f"Error loading file: {e}")
    with col_rst2:
        if st.button("Reset All", key="rst_portal", width="stretch"):
            reset_all()
            st.session_state.pop("last_portal_filename", None)
            st.rerun()

# ──────────────────────────────────────────────────────────────
# TAB 3 — CUSTOM REPORT BUILDER  (new, opt-in)
# ──────────────────────────────────────────────────────────────
with tab_custom:
    st.markdown(
        """
        <div class='section-card'>
            <h3>🔧 Custom Report Builder</h3>
            <div class='section-note'>
                Build a fully personalised report: assign column roles, define your own dashboard sections
                (tables, pivot counts, bar/pie charts, KPI cards), and add filter rules.
                The standard report (Tab 1 / Tab 2) is not affected.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if st.session_state.source_df is None:
        st.info(
            "Upload a file first using **📂 Upload Local File** or **🌐 Open External Portal**, "
            "then come back here to configure your custom report.",
            icon="💡",
        )
        st.stop()

    df = st.session_state.source_df
    all_cols = list(df.columns)
    numeric_cols = [c for c in all_cols if pd.api.types.is_numeric_dtype(df[c])]

    # ── Auto-detect on first load only (guard with flag) ─────────
    if not st.session_state.get("col_config_initialised"):
        detected = detect_col_config(df)
        st.session_state.col_config = detected
        if not st.session_state.section_configs:
            st.session_state.section_configs = default_section_configs(df, detected)
        st.session_state.col_config_initialised = True

    # ══════════════════════════════════════════════════════════
    # STEP 1 — COLUMN ROLES
    # ══════════════════════════════════════════════════════════
    with st.expander("**Step 1 — Column Roles**  ·  Assign columns to key report roles", expanded=True):
        cfg = st.session_state.col_config
        r1c1, r1c2 = st.columns(2)

        with r1c1:
            new_project = st.selectbox(
                "Project / Item Name Column",
                ["(none)"] + all_cols,
                index=(["(none)"] + all_cols).index(cfg["project"]) if cfg.get("project") in all_cols else 0,
                help="Primary row identifier — used in search and detail views.",
                key="cfg_project",
            )
            new_status = st.selectbox(
                "Status Column",
                ["(none)"] + all_cols,
                index=(["(none)"] + all_cols).index(cfg["status"]) if cfg.get("status") in all_cols else 0,
                help="Drives status charts and pivot tables.",
                key="cfg_status",
            )
            new_dates = st.multiselect(
                "Date Columns",
                all_cols,
                default=[c for c in (cfg.get("dates") or []) if c in all_cols],
                key="cfg_dates",
            )

        with r1c2:
            new_display = st.multiselect(
                "Display Columns  (shown in tables)",
                all_cols,
                default=[c for c in (cfg.get("display") or []) if c in all_cols],
                key="cfg_display",
            )
            new_metrics = st.multiselect(
                "Metric Columns  (numeric — KPI cards)",
                numeric_cols,
                default=[c for c in (cfg.get("metrics") or []) if c in numeric_cols],
                key="cfg_metrics",
            )

        if st.button("💾 Save Column Roles", key="save_col_cfg", type="primary"):
            st.session_state.col_config = {
                "project": None if new_project == "(none)" else new_project,
                "status": None if new_status == "(none)" else new_status,
                "dates": new_dates,
                "display": new_display,
                "metrics": new_metrics,
            }
            if not st.session_state.section_configs:
                st.session_state.section_configs = default_section_configs(df, st.session_state.col_config)
            st.success("Column roles saved.")

    # ══════════════════════════════════════════════════════════
    # STEP 2 — SECTION BUILDER
    # ══════════════════════════════════════════════════════════
    SECTION_TYPES = {
        "table":      "📋 Data Table",
        "pivot":      "🔢 Pivot / Count Table",
        "bar_chart":  "📊 Bar Chart",
        "pie_chart":  "🥧 Pie Chart",
        "kpi_cards":  "🔢 KPI Metric Cards",
    }
    AGG_OPTIONS = {
        "count":   "Count (rows)",
        "sum":     "Sum",
        "mean":    "Average",
        "nunique": "Count Distinct",
        "min":     "Minimum",
        "max":     "Maximum",
    }

    with st.expander(
        f"**Step 2 — Section Builder**  ·  {len(st.session_state.section_configs)} section(s) configured",
        expanded=bool(st.session_state.section_configs),
    ):
        _add_cols = st.columns([2, 2, 1])
        with _add_cols[0]:
            _new_type_label = st.selectbox(
                "Section Type",
                list(SECTION_TYPES.values()),
                index=1,
                key="new_sec_type",
            )
            _new_type = list(SECTION_TYPES.keys())[list(SECTION_TYPES.values()).index(_new_type_label)]
        with _add_cols[1]:
            _new_layout = st.radio(
                "Layout",
                ["↕ Vertical (full width)", "↔ Horizontal (half width)"],
                index=0,
                key="new_sec_layout",
                horizontal=True,
            )
        with _add_cols[2]:
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("➕ Add Section", key="add_section", type="primary"):
                st.session_state.section_configs.append({
                    "id": str(uuid.uuid4())[:8],
                    "title": f"Section {len(st.session_state.section_configs) + 1}",
                    "enabled": True,
                    "section_type": _new_type,
                    "layout": "horizontal" if "Horizontal" in _new_layout else "vertical",
                    "group_by": st.session_state.col_config.get("status"),
                    "agg_func": "count",
                    "agg_col": None,
                    "display_cols": (st.session_state.col_config.get("display") or [])[:6],
                    "sort_by": None,
                    "sort_asc": False,
                    "limit": None,
                })
                st.rerun()

        if not st.session_state.section_configs:
            st.info("No sections yet. Click **➕ Add New Section** above.", icon="💡")
        else:
            to_delete = None
            updated = []

            for i, sec in enumerate(st.session_state.section_configs):
                icon = "✅" if sec.get("enabled", True) else "⬜"
                with st.expander(f"{icon} {i+1}. {sec.get('title', 'Section')}", expanded=False):

                    sc1, sc2, sc3, sc4 = st.columns([3, 2, 2, 1])
                    with sc1:
                        sec["title"] = st.text_input("Title", value=sec["title"], key=f"t_{sec['id']}")
                    with sc2:
                        type_labels = list(SECTION_TYPES.values())
                        type_keys  = list(SECTION_TYPES.keys())
                        cur = type_keys.index(sec.get("section_type", "pivot")) if sec.get("section_type","pivot") in type_keys else 1
                        sec["section_type"] = type_keys[type_labels.index(
                            st.selectbox("Type", type_labels, index=cur, key=f"st_{sec['id']}")
                        )]
                    with sc3:
                        layout_opts = ["↕ Vertical (full width)", "↔ Horizontal (half width)"]
                        cur_layout  = 1 if sec.get("layout") == "horizontal" else 0
                        chosen = st.radio("Layout", layout_opts, index=cur_layout, key=f"ly_{sec['id']}", horizontal=True)
                        sec["layout"] = "horizontal" if "Horizontal" in chosen else "vertical"
                    with sc4:
                        sec["enabled"] = st.checkbox("Enabled", value=sec.get("enabled", True), key=f"en_{sec['id']}")

                    stype = sec["section_type"]

                    if stype in ("pivot", "bar_chart", "pie_chart"):
                        pa, pb, pc = st.columns(3)
                        with pa:
                            grp_opts = ["(none)"] + all_cols
                            grp_idx  = grp_opts.index(sec.get("group_by")) if sec.get("group_by") in all_cols else 0
                            g = st.selectbox("Group By", grp_opts, index=grp_idx, key=f"grp_{sec['id']}")
                            sec["group_by"] = None if g == "(none)" else g
                        with pb:
                            agg_labels = list(AGG_OPTIONS.values())
                            agg_keys   = list(AGG_OPTIONS.keys())
                            agg_idx    = agg_keys.index(sec.get("agg_func","count")) if sec.get("agg_func","count") in agg_keys else 0
                            sec["agg_func"] = agg_keys[agg_labels.index(
                                st.selectbox("Aggregation", agg_labels, index=agg_idx, key=f"agg_{sec['id']}")
                            )]
                        with pc:
                            if sec["agg_func"] in ("sum","mean","min","max","nunique"):
                                av_opts = ["(none)"] + all_cols
                                av_idx  = av_opts.index(sec.get("agg_col")) if sec.get("agg_col") in all_cols else 0
                                av = st.selectbox("Value Column", av_opts, index=av_idx, key=f"av_{sec['id']}")
                                sec["agg_col"] = None if av == "(none)" else av

                    elif stype == "table":
                        sec["display_cols"] = st.multiselect(
                            "Columns to Display", all_cols,
                            default=[c for c in sec.get("display_cols",[]) if c in all_cols],
                            key=f"dc_{sec['id']}",
                        )
                        ta, tb, tc = st.columns(3)
                        with ta:
                            so = ["(none)"] + all_cols
                            si = so.index(sec.get("sort_by")) if sec.get("sort_by") in all_cols else 0
                            sv = st.selectbox("Sort By", so, index=si, key=f"sb_{sec['id']}")
                            sec["sort_by"] = None if sv == "(none)" else sv
                        with tb:
                            sec["sort_asc"] = st.selectbox(
                                "Direction", ["Descending","Ascending"],
                                index=1 if sec.get("sort_asc") else 0,
                                key=f"sd_{sec['id']}",
                            ) == "Ascending"
                        with tc:
                            sec["limit"] = st.number_input(
                                "Max Rows (0 = all)", min_value=0,
                                value=int(sec.get("limit") or 0),
                                key=f"lim_{sec['id']}",
                            ) or None

                    elif stype == "kpi_cards":
                        sec["display_cols"] = st.multiselect(
                            "Metric / Display Columns", all_cols,
                            default=[c for c in sec.get("display_cols",[]) if c in all_cols],
                            key=f"kc_{sec['id']}",
                        )
                        agg_labels = list(AGG_OPTIONS.values())
                        agg_keys   = list(AGG_OPTIONS.keys())
                        agg_idx    = agg_keys.index(sec.get("agg_func","count")) if sec.get("agg_func","count") in agg_keys else 0
                        sec["agg_func"] = agg_keys[agg_labels.index(
                            st.selectbox("Aggregation", agg_labels, index=agg_idx, key=f"ka_{sec['id']}")
                        )]

                    # ── Live preview ──────────────────────────────
                    if st.checkbox("👁️ Preview this section", key=f"prev_{sec['id']}"):
                        try:
                            from core.engine import build_section_data
                            preview_data = build_section_data(df, sec)
                            if isinstance(preview_data, pd.DataFrame):
                                if preview_data.empty:
                                    st.info("No data — check your Group By / column settings.")
                                else:
                                    st.dataframe(preview_data.head(10), use_container_width=True, hide_index=True)
                            elif isinstance(preview_data, dict):
                                items = list(preview_data.items())
                                kpi_cols = st.columns(min(len(items), 4))
                                for ki, (name, val) in enumerate(items):
                                    kpi_cols[ki % 4].metric(name, f"{val:,}" if isinstance(val, (int, float)) else val)
                        except Exception as _pe:
                            st.warning(f"Preview unavailable: {_pe}")

                    if st.button("🗑️ Remove Section", key=f"del_{sec['id']}"):
                        to_delete = sec["id"]

                    updated.append(sec)

            if to_delete:
                st.session_state.section_configs = [s for s in updated if s["id"] != to_delete]
                st.rerun()
            else:
                st.session_state.section_configs = updated

    # ══════════════════════════════════════════════════════════
    # STEP 3 — FILTER RULES
    # ══════════════════════════════════════════════════════════
    OPERATORS = {
        "contains":     "Contains",
        "not_contains": "Does not contain",
        "equals":       "Equals",
        "not_equals":   "Not equals",
        "starts_with":  "Starts with",
        "ends_with":    "Ends with",
        "in_list":      "In list (comma-sep)",
        "not_in_list":  "Not in list",
        "greater_than": "> Greater than",
        "less_than":    "< Less than",
        "gte":          "≥ Greater or equal",
        "lte":          "≤ Less or equal",
        "is_empty":     "Is empty",
        "is_not_empty": "Is not empty",
    }

    n_rules = len(st.session_state.filter_rules)
    with st.expander(
        f"**Step 3 — Filter Rules**  ·  {n_rules} rule(s) active",
        expanded=False,
    ):
        # Add rule row
        fa, fb, fc, fd, fe = st.columns([2, 2, 2, 1, 1])
        with fa:
            f_col = st.selectbox("Column", all_cols, key="f_col")
        with fb:
            op_labels = list(OPERATORS.values())
            op_keys   = list(OPERATORS.keys())
            f_op_lbl  = st.selectbox("Operator", op_labels, key="f_op")
            f_op      = op_keys[op_labels.index(f_op_lbl)]
        with fc:
            needs_val = f_op not in ("is_empty","is_not_empty")
            if needs_val:
                hints = sorted(df[f_col].dropna().astype(str).unique())[:5]
                f_val = st.text_input("Value", placeholder=f"e.g. {', '.join(hints)}", key="f_val")
            else:
                f_val = ""
                st.text_input("Value", value="(not required)", disabled=True, key="f_val")
        with fd:
            f_conn = st.selectbox("Join", ["AND","OR"], key="f_connector")
        with fe:
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("➕ Add Rule", type="primary", key="add_frule"):
                st.session_state.filter_rules.append({
                    "id": str(uuid.uuid4())[:8],
                    "col": f_col, "op": f_op, "val": f_val, "connector": f_conn,
                })
                st.rerun()

        # Active rules
        if not st.session_state.filter_rules:
            st.info("No rules yet. All rows will be included.", icon="ℹ️")
        else:
            del_rule = None
            for idx, rule in enumerate(st.session_state.filter_rules):
                rc1,rc2,rc3,rc4,rc5 = st.columns([1,2,2,2,1])
                with rc1:
                    lbl = rule.get("connector","AND") if idx > 0 else "WHERE"
                    st.markdown(f"<span style='color:#5a6275;font-size:0.82rem;'>{lbl}</span>", unsafe_allow_html=True)
                with rc2:
                    st.markdown(f"**{rule['col']}**")
                with rc3:
                    st.markdown(f"<span style='color:#1a3a8c;'>{OPERATORS.get(rule['op'],rule['op'])}</span>", unsafe_allow_html=True)
                with rc4:
                    st.markdown(f"`{rule['val']}`" if rule['val'] else "—")
                with rc5:
                    if st.button("✕", key=f"dr_{rule['id']}"):
                        del_rule = rule["id"]

            if del_rule:
                st.session_state.filter_rules = [r for r in st.session_state.filter_rules if r["id"] != del_rule]
                st.rerun()

            if st.button("🗑️ Clear All Rules", key="clear_rules"):
                st.session_state.filter_rules = []
                st.rerun()

        # Live preview metrics
        try:
            filtered_prev = apply_filter_rules(df, st.session_state.filter_rules)
            pv1, pv2, pv3 = st.columns(3)
            pv1.metric("Total Rows", len(df))
            pv2.metric("After Filters", len(filtered_prev),
                       delta=f"-{len(df)-len(filtered_prev)}" if len(df) != len(filtered_prev) else None,
                       delta_color="inverse")
            pv3.metric("Active Rules", n_rules)
        except Exception:
            pass

    # ══════════════════════════════════════════════════════════
    # GENERATE CUSTOM REPORT
    # ══════════════════════════════════════════════════════════
    st.divider()

    active_sections = [s for s in st.session_state.section_configs if s.get("enabled", True)]

    gc1, gc2 = st.columns([3, 1])
    with gc1:
        week_mode_custom = st.selectbox(
            "Week Mode",
            ["last", "current"],
            index=0 if st.session_state.get("week_mode","last") == "last" else 1,
            key="custom_week_mode",
        )
    with gc2:
        st.markdown("<br>", unsafe_allow_html=True)

    gb1, gb2 = st.columns(2)
    with gb1:
        if st.button("🚀 Generate Custom Report", type="primary", width="stretch", key="gen_custom"):
            if not active_sections:
                st.error("Add at least one enabled section in **Step 2 — Section Builder** above.")
            else:
                try:
                    with st.spinner("Building custom report…"):
                        rpt = build_report_from_config(
                            df,
                            col_config=st.session_state.col_config,
                            section_configs=st.session_state.section_configs,
                            filter_rules=st.session_state.filter_rules,
                            week_mode=week_mode_custom,
                        )
                    st.session_state.report = rpt
                    st.session_state.working_df = rpt["working"].copy()
                    st.session_state.week_mode = week_mode_custom
                    st.session_state.awaiting_next_action = True
                    add_chat(
                        "assistant",
                        f"Custom report generated: {len(rpt['working'])} rows, "
                        f"{len(rpt['sections'])} sections. Navigate to 📊 Dashboard.",
                    )
                    st.success(
                        f"✅ Custom report ready — **{len(active_sections)} sections**, "
                        f"**{len(rpt['working'])} rows**. Go to **📊 Dashboard** to view it."
                    )
                except Exception as e:
                    st.error(f"Error generating custom report: {e}")
    with gb2:
        if st.button("♻️ Reset Custom Config", width="stretch", key="rst_custom"):
            st.session_state.col_config = {
                "project": None, "status": None,
                "dates": [], "display": [], "metrics": [],
            }
            st.session_state.section_configs = []
            st.session_state.filter_rules = []
            st.rerun()

# ──────────────────────────────────────────────────────────────
# GLOBAL STATUS INDICATOR
# ──────────────────────────────────────────────────────────────
st.divider()
if st.session_state.report is not None:
    rpt = st.session_state.report
    src_label = st.session_state.get("last_portal_filename") or "local file"
    n_sec = len(rpt.get("sections") or [])
    mode_label = f"Custom · {n_sec} sections" if n_sec else "Auto (standard report)"
    st.success(
        f"✅ Active report: **{rpt.get('week_range','N/A')}** | "
        f"{len(st.session_state.working_df)} rows | "
        f"Mode: *{mode_label}* | Source: *{src_label}* → Navigate to **📊 Dashboard**"
    )
else:
    st.info(
        "No report loaded yet. Upload a file and click **Generate Initial Report** "
        "(or use **🔧 Custom Report Builder** for a personalised report)."
    )
