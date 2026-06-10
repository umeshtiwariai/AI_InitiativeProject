import streamlit as st

from core.engine import (
    init_state, inject_styles,
    add_chat, generate_from_prompt, build_report,
    is_project_details_request, project_details_response,
    wants_email, wants_modify, wants_export, get_export_format,
    is_week_report_request, parse_week_mode, parse_emails,
    send_email, export_pdf, export_ppt, export_image, export_excel,
)
from core.downloader import is_url_download_request, extract_url_from_text

st.set_page_config(page_title="AI Chat – Smart WSR", page_icon="🤖", layout="wide")
init_state()
inject_styles()

st.markdown(
    """
    <div class='app-header'>
        <div>
            <h1>🤖 Smart WSR AI Chat Agent</h1>
            <p class='subtitle'>Ask the agent to filter, modify, export, or retrieve project details.</p>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

if st.session_state.source_df is None:
    st.warning("No data loaded. Please go to **Home**, upload a file and click **Generate Initial Report** first.")
    st.stop()

# ── Chat history ──────────────────────────────────────────────
for row in st.session_state.chat_history:
    with st.chat_message(row["role"]):
        st.write(row["msg"])

# ── Portal redirect button (shown when agent detected a portal URL) ──
if st.session_state.get("_portal_redirect_url"):
    st.link_button(
        "🌐 Open Portal in New Tab",
        st.session_state["_portal_redirect_url"],
        width='content',
        type="primary",
    )

# ── Export download button (shown after export request) ───────
if st.session_state.get("show_download") and st.session_state.get("export_file"):
    st.subheader("📥 Export Download")
    try:
        with open(st.session_state.export_file, "rb") as f:
            st.download_button(
                f"Download {st.session_state.export_filename}",
                f,
                file_name=st.session_state.export_filename,
                mime="application/octet-stream",
                width='stretch',
            )
    except Exception as e:
        st.error(f"Error loading export file: {e}")

# ── Chat input ────────────────────────────────────────────────
prompt = st.chat_input(
    "Ask me to generate reports, filter data, export, or search projects "
    "(e.g. 'Show only UAT projects', 'Export as PDF', 'Tell me about ProjectX')"
)

if not prompt:
    st.stop()

add_chat("user", prompt)

# ── Portal URL mention → redirect user ───────────────────────
if is_url_download_request(prompt):
    url = extract_url_from_text(prompt)
    if url:
        st.session_state["_portal_redirect_url"] = url
        add_chat(
            "assistant",
            f"I found this portal link: {url}\n\n"
            "Please open it in your browser, download the file, then upload it on the **🏠 Home** page "
            "under the **🌐 Open External Portal** tab to generate the report.",
        )
    else:
        add_chat("assistant", "I couldn't find a valid URL in your message. Please paste the full https:// link.")
    st.rerun()

# Guard: report must exist for most actions
if st.session_state.report is None and not is_week_report_request(prompt):
    add_chat("assistant", "Please generate the initial report on the Home page first.")
    st.rerun()

old_rows = len(st.session_state.working_df) if st.session_state.working_df is not None else 0

# ── Week report generation ────────────────────────────────────
if is_week_report_request(prompt):
    mode = parse_week_mode(prompt)
    rpt = build_report(st.session_state.source_df, week_mode=mode)
    rpt["working"] = st.session_state.source_df.copy()
    rpt["filter_criteria"] = {}
    st.session_state.week_mode = mode
    st.session_state.report = rpt
    st.session_state.working_df = rpt["working"].copy()
    st.session_state.awaiting_next_action = True
    add_chat("assistant", f"Report generated for {mode} week. Navigate to 📊 Dashboard to view it.")
    st.rerun()

# ── Email flow ────────────────────────────────────────────────
if st.session_state.awaiting_email:
    emails = parse_emails(prompt)
    if not emails:
        add_chat("assistant", "Please provide valid recipient email IDs separated by semicolons.")
        st.rerun()
    ok, msg = send_email(emails, st.session_state.report)
    add_chat("assistant", msg)
    st.session_state.awaiting_email = False
    add_chat("assistant", "Any further modification required or want to export?")
    st.rerun()

# ── Export request ────────────────────────────────────────────
if wants_export(prompt):
    if st.session_state.report is None:
        add_chat("assistant", "Please generate a report first before requesting export.")
        st.rerun()
    fmt = get_export_format(prompt)
    if fmt is None:
        add_chat("assistant", "Please specify the export format: PDF, PPT, Image (PNG), or Excel.")
        st.rerun()
    try:
        if fmt == "pdf":
            fpath = export_pdf(st.session_state.report)
            fname = "WSR_Report.pdf"
        elif fmt == "ppt":
            fpath = export_ppt(st.session_state.report)
            fname = "WSR_Report.pptx"
        elif fmt == "image":
            fpath = export_image(st.session_state.report)
            fname = "WSR_Report.png"
        else:
            fpath = export_excel(st.session_state.report)
            fname = "WSR_Final.xlsx"
        st.session_state.export_file = str(fpath)
        st.session_state.export_filename = fname
        st.session_state.show_download = True
        add_chat("assistant", f"✅ {fmt.upper()} export ready! Click the download button above.")
    except Exception as e:
        add_chat("assistant", f"❌ Failed to generate {fmt.upper()} export: {e}")
    st.rerun()

# ── Send email request ────────────────────────────────────────
if wants_email(prompt):
    st.session_state.awaiting_email = True
    add_chat("assistant", "Please provide recipient email IDs separated by semicolons.")
    st.rerun()

# ── Project detail request ────────────────────────────────────
if is_project_details_request(prompt):
    details = project_details_response(prompt)
    add_chat("assistant", details)
    st.session_state.project_query = prompt
    st.session_state.project_details = details
    st.session_state.awaiting_next_action = True
    st.rerun()

# ── Modify / filter request ───────────────────────────────────
if wants_modify(prompt):
    rpt = generate_from_prompt(prompt)
    new_rows = len(st.session_state.working_df)
    add_chat("assistant", f"Report regenerated. Rows changed from {old_rows} to {new_rows}. View in 📊 Dashboard.")
    st.rerun()

add_chat("assistant", "Please tell me if you want report modification, export (PDF/PPT/Image/Excel), project details, or send email.")
st.rerun()
