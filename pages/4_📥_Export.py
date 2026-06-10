import streamlit as st

from core.engine import (
    init_state, inject_styles, get_report_title,
    export_pdf, export_ppt, export_image, export_excel,
    send_email, parse_emails,
)

st.set_page_config(page_title="Export – Smart WSR", page_icon="📥", layout="wide")
init_state()
inject_styles()

st.markdown(
    """
    <div class='app-header'>
        <div>
            <h1>📥 Export & Email</h1>
            <p class='subtitle'>Download the report as PDF, PPT, Image, or Excel — or send it via email.</p>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

report = st.session_state.get("report")

if report is None:
    st.warning("No report loaded. Please go to **Home**, upload a file and click **Generate Initial Report** first.")
    st.stop()

st.info(f"Exporting: **{get_report_title(report)}**")

# ── Download buttons ──────────────────────────────────────────
st.markdown(
    """
    <div class='section-card'>
        <h3>Download Report</h3>
        <div class='section-note'>Click any format to generate and download the report file.</div>
    </div>
    """,
    unsafe_allow_html=True,
)

c1, c2, c3, c4 = st.columns(4)

with c1:
    if st.button("Generate PDF", width='stretch', type="primary"):
        with st.spinner("Generating PDF…"):
            try:
                f = export_pdf(report)
                with open(f, "rb") as fp:
                    st.download_button(
                        "⬇️ Download PDF",
                        fp,
                        file_name=f.name,
                        mime="application/pdf",
                        width='stretch',
                    )
                st.success("PDF ready.")
            except Exception as e:
                st.error(f"PDF export failed: {e}")

with c2:
    if st.button("Generate PPT", width='stretch', type="primary"):
        with st.spinner("Generating PPT…"):
            try:
                f = export_ppt(report)
                with open(f, "rb") as fp:
                    st.download_button(
                        "⬇️ Download PPT",
                        fp,
                        file_name=f.name,
                        mime="application/vnd.openxmlformats-officedocument.presentationml.presentation",
                        width='stretch',
                    )
                st.success("PPT ready.")
            except Exception as e:
                st.error(f"PPT export failed: {e}")

with c3:
    if st.button("Generate Image", width='stretch', type="primary"):
        with st.spinner("Generating image…"):
            try:
                f = export_image(report)
                with open(f, "rb") as fp:
                    st.download_button(
                        "⬇️ Download PNG",
                        fp,
                        file_name=f.name,
                        mime="image/png",
                        width='stretch',
                    )
                st.success("Image ready.")
            except Exception as e:
                st.error(f"Image export failed: {e}")

with c4:
    if st.button("Generate Excel", width='stretch', type="primary"):
        with st.spinner("Generating Excel…"):
            try:
                f = export_excel(report)
                with open(f, "rb") as fp:
                    st.download_button(
                        "⬇️ Download Excel",
                        fp,
                        file_name=f.name,
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        width='stretch',
                    )
                st.success("Excel ready.")
            except Exception as e:
                st.error(f"Excel export failed: {e}")

st.divider()

# ── Email report ──────────────────────────────────────────────
st.markdown(
    """
    <div class='section-card'>
        <h3>Send Report via Email</h3>
        <div class='section-note'>Sends the report image and Excel file to the specified recipients. Configure SMTP on the ⚙️ Settings page first.</div>
    </div>
    """,
    unsafe_allow_html=True,
)

email_input = st.text_input(
    "Recipient Emails",
    placeholder="user1@company.com; user2@company.com",
    help="Separate multiple addresses with semicolons or commas.",
)

if st.button("Send Email", width='stretch'):
    if not email_input.strip():
        st.warning("Enter at least one recipient email address.")
    else:
        recipients = parse_emails(email_input)
        if not recipients:
            st.error("No valid email addresses found. Check the format (e.g. user@domain.com).")
        elif not st.session_state.smtp_user or not st.session_state.smtp_pass:
            st.warning("SMTP credentials are not configured. Go to ⚙️ **Settings** to set them up.")
        else:
            with st.spinner("Sending email…"):
                ok, msg = send_email(recipients, report)
            if ok:
                st.success(msg)
            else:
                st.error(msg)
