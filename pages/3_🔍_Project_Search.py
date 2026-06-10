import streamlit as st
import pandas as pd

from core.engine import (
    init_state, inject_styles,
    find_project_rows, format_project_details,
    apply_filter_rules, build_report_from_config,
)

st.set_page_config(page_title="Project Search – Smart WSR", page_icon="🔍", layout="wide")
init_state()
inject_styles()

st.markdown(
    """
    <div class='app-header'>
        <div>
            <h1>🔍 Project Search & Filters</h1>
            <p class='subtitle'>Search by keyword and apply ad-hoc column filters — results update the active report.</p>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

if st.session_state.source_df is None:
    st.warning("No data loaded. Go to **🏠 Home**, upload a file and click **🚀 Generate Report** first.")
    st.stop()

src = st.session_state.source_df
col_config = st.session_state.col_config
all_cols = list(src.columns)

project_col = col_config.get("project")
status_col = col_config.get("status")
display_cols = col_config.get("display") or all_cols[:8]
numeric_cols = [c for c in all_cols if pd.api.types.is_numeric_dtype(src[c])]

# ══════════════════════════════════════════════════════════════
# QUICK SEARCH
# ══════════════════════════════════════════════════════════════
st.markdown(
    """
    <div class='section-card'>
        <h3>Quick Search</h3>
        <div class='section-note'>
            Search across all text columns or narrow to the configured Project column.
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

qs1, qs2, qs3 = st.columns([3, 1, 1])
with qs1:
    query = st.text_input(
        "Search keyword",
        placeholder="Project name, module ID, keyword…",
        key="search_query",
    )
with qs2:
    search_scope = st.selectbox(
        "Search in",
        (["Project Column"] if project_col else []) + ["All Text Columns"],
        key="search_scope",
    )
with qs3:
    st.markdown("<br>", unsafe_allow_html=True)
    do_search = st.button("🔍 Search", type="primary", width="stretch")

if do_search:
    if not query.strip():
        st.warning("Enter a keyword to search.")
    else:
        try:
            if search_scope == "Project Column" and project_col and project_col in src.columns:
                mask = src[project_col].astype(str).str.contains(query.strip(), case=False, na=False)
                rows = src[mask]
            else:
                # Search all object/string columns
                mask = pd.Series([False] * len(src), index=src.index)
                for col in src.columns:
                    if src[col].dtype == object or src[col].dtype.name == "string":
                        mask |= src[col].astype(str).str.contains(query.strip(), case=False, na=False)
                rows = src[mask]

            if rows.empty:
                st.info("No matching rows found. Try a different keyword.")
            else:
                st.success(f"Found **{len(rows)}** matching row(s). Showing up to 20.")
                show_cols = [c for c in display_cols if c in rows.columns] or list(rows.columns)
                st.dataframe(rows[show_cols].head(20), width="stretch", hide_index=True)

                # Project detail card
                if project_col and project_col in rows.columns:
                    details = format_project_details(rows, src)
                    if details:
                        with st.expander("📋 Detail View", expanded=False):
                            st.markdown(details, unsafe_allow_html=True)
        except Exception as e:
            st.error(f"Search error: {e}")

st.divider()

# ══════════════════════════════════════════════════════════════
# ADVANCED COLUMN FILTERS
# ══════════════════════════════════════════════════════════════
st.markdown(
    """
    <div class='section-card'>
        <h3>Advanced Column Filters</h3>
        <div class='section-note'>
            Filter any column with multiple conditions. Click
            <strong>Apply & Rebuild Report</strong> to update the 📊 Dashboard.
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

OPERATORS = {
    "contains": "Contains",
    "not_contains": "Does not contain",
    "equals": "Equals",
    "not_equals": "Not equals",
    "in_list": "In list (comma-sep)",
    "not_in_list": "Not in list",
    "greater_than": "> Greater than",
    "less_than": "< Less than",
    "gte": "≥ Greater or equal",
    "lte": "≤ Less or equal",
    "is_empty": "Is empty",
    "is_not_empty": "Is not empty",
}

# ── Status filter shortcut (if status col detected) ───────────
if status_col and status_col in src.columns:
    st.markdown("**Status Filter (quick)**")
    unique_statuses = sorted(src[status_col].dropna().astype(str).unique())
    selected_statuses = st.multiselect(
        f"Filter by {status_col}",
        unique_statuses,
        default=[],
        key="status_filter_quick",
    )
    st.markdown("---")

# ── General column filters ────────────────────────────────────
st.markdown("**General Column Filters**")

if "adv_filters" not in st.session_state:
    st.session_state.adv_filters = []

af1, af2, af3, af4, af5 = st.columns([2, 2, 2, 1, 1])
with af1:
    af_col = st.selectbox("Column", all_cols, key="af_col")
with af2:
    op_labels = list(OPERATORS.values())
    op_keys = list(OPERATORS.keys())
    af_op_label = st.selectbox("Operator", op_labels, key="af_op")
    af_op = op_keys[op_labels.index(af_op_label)]
with af3:
    needs_val = af_op not in ("is_empty", "is_not_empty")
    if needs_val:
        unique_hints = sorted(src[af_col].dropna().astype(str).unique())[:5]
        af_val = st.text_input("Value", placeholder=f"e.g. {', '.join(unique_hints)}", key="af_val")
    else:
        af_val = ""
        st.text_input("Value", value="(not required)", disabled=True, key="af_val")
with af4:
    af_conn = st.selectbox("Join", ["AND", "OR"], key="af_connector")
with af5:
    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("➕ Add", key="add_adv_filter"):
        import uuid
        st.session_state.adv_filters.append({
            "id": str(uuid.uuid4())[:8],
            "col": af_col, "op": af_op, "val": af_val, "connector": af_conn,
        })
        st.rerun()

# ── Show active ad-hoc filters ────────────────────────────────
if st.session_state.adv_filters:
    st.markdown(f"**Active Filters ({len(st.session_state.adv_filters)})**")
    del_filter = None
    for idx, f in enumerate(st.session_state.adv_filters):
        fc1, fc2, fc3, fc4, fc5 = st.columns([1, 2, 2, 2, 1])
        with fc1:
            st.markdown(f"<span style='color:#5a6275;font-size:0.82rem;'>{f.get('connector','AND') if idx > 0 else 'WHERE'}</span>", unsafe_allow_html=True)
        with fc2:
            st.markdown(f"**{f['col']}**")
        with fc3:
            st.markdown(f"<span style='color:#1a3a8c;'>{OPERATORS.get(f['op'], f['op'])}</span>", unsafe_allow_html=True)
        with fc4:
            st.markdown(f"`{f['val']}`" if f['val'] else "—")
        with fc5:
            if st.button("✕", key=f"del_af_{f['id']}"):
                del_filter = f["id"]

    if del_filter:
        st.session_state.adv_filters = [f for f in st.session_state.adv_filters if f["id"] != del_filter]
        st.rerun()

# ── Numeric range filters for metric columns ──────────────────
numeric_filters = {}
if numeric_cols:
    with st.expander("Numeric Range Filters", expanded=False):
        nr_cols = st.columns(min(len(numeric_cols), 3))
        for i, nc in enumerate(numeric_cols[:6]):
            col_min = float(src[nc].min(skipna=True))
            col_max = float(src[nc].max(skipna=True))
            if col_min < col_max:
                sel = nr_cols[i % 3].slider(
                    nc, min_value=col_min, max_value=col_max,
                    value=(col_min, col_max), key=f"nr_{nc}",
                )
                if sel != (col_min, col_max):
                    numeric_filters[nc] = sel

st.divider()

# ── Apply & preview ───────────────────────────────────────────
bc1, bc2, bc3 = st.columns([2, 2, 1])
with bc1:
    apply_btn = st.button("🔄 Apply & Rebuild Report", type="primary", width="stretch")
with bc2:
    if st.button("🗑️ Clear All Filters", width="stretch"):
        st.session_state.adv_filters = []
        st.rerun()
with bc3:
    pass

if apply_btn:
    try:
        filtered = src.copy()

        # Status shortcut
        if status_col and status_col in filtered.columns and selected_statuses:
            filtered = filtered[
                filtered[status_col].astype(str).isin(selected_statuses)
            ]

        # Numeric ranges
        for nc, (lo, hi) in numeric_filters.items():
            if nc in filtered.columns:
                filtered = filtered[
                    pd.to_numeric(filtered[nc], errors="coerce").between(lo, hi)
                ]

        # Ad-hoc column filters
        filtered = apply_filter_rules(filtered, st.session_state.adv_filters)

        if filtered.empty:
            st.warning("No rows match the current filters. Adjust and try again.")
        else:
            st.session_state.working_df = filtered.copy()

            # Rebuild report using current section configs
            rpt = build_report_from_config(
                filtered,
                col_config=st.session_state.col_config,
                section_configs=st.session_state.section_configs,
                filter_rules=st.session_state.adv_filters,
                week_mode=st.session_state.get("week_mode", "last"),
            )
            rpt["filter_criteria"] = rpt.get("filter_criteria", {})
            if status_col and selected_statuses:
                rpt["filter_criteria"][status_col] = f"in {selected_statuses}"
            st.session_state.report = rpt

            st.success(f"✅ Filters applied — {len(filtered)} rows remaining. Navigate to 📊 Dashboard.")

            # Preview
            show_cols = [c for c in display_cols if c in filtered.columns] or list(filtered.columns)
            st.dataframe(filtered[show_cols].head(15), width="stretch", hide_index=True)

    except Exception as e:
        st.error(f"Filter error: {e}")
