import streamlit as st

from core.engine import init_state, inject_styles, test_smtp_connection

st.set_page_config(page_title="Settings – Smart WSR", page_icon="⚙️", layout="wide")
init_state()
inject_styles()

st.markdown(
    """
    <div class='app-header'>
        <div>
            <h1>⚙️ Settings</h1>
            <p class='subtitle'>Configure SMTP email settings and test connectivity.</p>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

# ── SMTP Settings ─────────────────────────────────────────────
st.markdown(
    """
    <div class='section-card'>
        <h3>Email / SMTP Configuration</h3>
        <div class='section-note'>Required for sending reports via email from the 📥 Export page.</div>
    </div>
    """,
    unsafe_allow_html=True,
)

col1, col2 = st.columns(2)

with col1:
    st.session_state.smtp_host = st.text_input(
        "SMTP Host",
        value=st.session_state.smtp_host,
        placeholder="smtp.office365.com",
    )
    st.session_state.smtp_port = st.text_input(
        "SMTP Port",
        value=st.session_state.smtp_port,
        placeholder="587",
    )
    st.session_state.smtp_sender = st.text_input(
        "Sender Email",
        value=st.session_state.smtp_sender,
        placeholder="your-name@company.com",
    )

with col2:
    st.session_state.smtp_user = st.text_input(
        "SMTP User",
        value=st.session_state.smtp_user,
        placeholder="your-email@company.com",
    )
    st.session_state.smtp_pass = st.text_input(
        "SMTP Password",
        value=st.session_state.smtp_pass,
        type="password",
        placeholder="App password or SMTP password",
    )

st.caption("💡 If 2-Factor Authentication is enabled, generate an App Password from your email provider.")

st.divider()

# ── Connection test ───────────────────────────────────────────
st.markdown(
    """
    <div class='section-card'>
        <h3>Connection Diagnostics</h3>
        <div class='section-note'>Test the SMTP settings without sending an actual email.</div>
    </div>
    """,
    unsafe_allow_html=True,
)

if st.button("🔍 Test SMTP Connection", width='content'):
    with st.spinner("Testing SMTP connection…"):
        results = test_smtp_connection()
    with st.container(border=True):
        st.markdown("### Diagnostic Steps")
        for step in results.get("steps", []):
            st.write(step)
        status = results.get("status", "UNKNOWN")
        if status == "SUCCESS":
            st.success("✅ All tests passed! Your email settings are correctly configured.")
        elif status == "FAILED":
            st.error("❌ Connection test failed. See details above.")
            if results.get("error"):
                st.code(results["error"], language="text")
        else:
            st.info("Test did not complete. Check your settings and try again.")

st.divider()

# ── Week mode ─────────────────────────────────────────────────
st.markdown(
    """
    <div class='section-card'>
        <h3>Report Settings</h3>
        <div class='section-note'>Controls which week's deliveries are highlighted in the report.</div>
    </div>
    """,
    unsafe_allow_html=True,
)

st.session_state.week_mode = st.selectbox(
    "Default Week Mode",
    options=["last", "current"],
    index=0 if st.session_state.get("week_mode", "last") == "last" else 1,
    help="'last' = last Mon-Fri window; 'current' = this Mon-Fri window.",
)
st.caption("Changes apply to the next **Generate Initial Report** or AI Chat regeneration.")
