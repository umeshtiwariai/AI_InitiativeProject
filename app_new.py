import os
from pathlib import Path
from datetime import datetime
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email.mime.text import MIMEText
from email import encoders

import pandas as pd
import streamlit as st
from langchain_core.messages import HumanMessage

from agents.report_agent import generate_summary as generate_report_summary
from agents.revise_agent import revise_report
from agents.summary_agent import generate_bullets
from agents.retrieval_agent import answer_question
from services.report_engine import generate_report
from services.export_service import export_pdf, export_ppt, export_png

APP_NAME = 'Smart WSR Multi-Agent RAG'
BASE_DIR = Path(__file__).resolve().parent

st.set_page_config(page_title=APP_NAME, page_icon='📊', layout='wide')

# Custom CSS for better styling
st.markdown("""
    <style>
        .main-header {
            color: #2e7d32;
            border-bottom: 3px solid #2e7d32;
            padding-bottom: 10px;
            margin-bottom: 20px;
        }
        .section-header {
            color: #2e7d32;
            background-color: #f3f3f3;
            padding: 10px;
            border-radius: 5px;
            margin-top: 20px;
            margin-bottom: 10px;
        }
        .metric-box {
            background-color: #f3f3f3;
            padding: 15px;
            border-radius: 5px;
            border-left: 4px solid #2e7d32;
        }
    </style>
""", unsafe_allow_html=True)

# Initialize session state
if 'report' not in st.session_state:
    st.session_state.report = None
if 'chat_history' not in st.session_state:
    st.session_state.chat_history = []
if 'filtered_df' not in st.session_state:
    st.session_state.filtered_df = None
if 'smtp_settings' not in st.session_state:
    st.session_state.smtp_settings = {
        'host': 'smtp.office365.com',
        'port': 587,
        'user': '',
        'pass': '',
        'sender': 'umesh.tiwari@businessnext.com'
    }

# PAGE TITLE
st.markdown("<h1 class='main-header'>📊 Smart WSR Multi-Agent RAG</h1>", unsafe_allow_html=True)

# ============================================================
# SIDEBAR CONFIGURATION
# ============================================================

st.sidebar.header('Upload and Configuration')
api_key = st.sidebar.text_input(
    'Gemini API Key',
    type='password',
    help='Your Gemini API key for LangChain calls'
).strip()

uploaded_files = st.sidebar.file_uploader(
    'Upload project status CSV or Excel files',
    type=['csv', 'xlsx'],
    accept_multiple_files=True
)

st.sidebar.subheader('Settings')
week_mode = st.sidebar.selectbox('Week Mode', ['last', 'current'], index=0)

with st.sidebar.expander('📧 SMTP Email Settings', expanded=False):
    st.session_state.smtp_settings['host'] = st.text_input('SMTP Host', st.session_state.smtp_settings['host'])
    st.session_state.smtp_settings['port'] = st.number_input('SMTP Port', value=st.session_state.smtp_settings['port'])
    st.session_state.smtp_settings['user'] = st.text_input('SMTP User')
    st.session_state.smtp_settings['pass'] = st.text_input('SMTP Password', type='password')
    st.session_state.smtp_settings['sender'] = st.text_input('Sender Email', st.session_state.smtp_settings['sender'])

# Process uploaded files
if uploaded_files:
    try:
        st.session_state.report = generate_report(uploaded_files)
        st.success('✅ Data loaded and report created successfully.')
    except Exception as err:
        st.error(f'❌ Unable to process uploaded files: {err}')

# ============================================================
# DATA PREVIEW
# ============================================================

if st.session_state.report is not None:
    with st.expander('📋 Source Dataset Preview', expanded=False):
        st.dataframe(st.session_state.report['raw'].head(10), use_container_width=True)

# ============================================================
# MAIN REPORT RENDERING (5 Sections)
# ============================================================

if st.session_state.report is not None:
    st.markdown("<div class='section-header'><h2>📈 Report Overview</h2></div>", unsafe_allow_html=True)
    st.markdown("**Summary metrics from current dataset**")
    
    # Section 1: Project Status Summary
    col1, col2, col3, col4, col5, col6, col7 = st.columns(7)
    summary = st.session_state.report['summary']
    if not summary.empty:
        metrics = summary.iloc[0].to_dict()
        col1.metric('Go Live', metrics.get('Go Live', 0))
        col2.metric('Development', metrics.get('Development', 0))
        col3.metric('UAT', metrics.get('UAT', 0))
        col4.metric('In UD', metrics.get('In UD', 0))
        col5.metric('PO Awaited', metrics.get('PO Awaited', 0))
        col6.metric('UD Not Started', metrics.get('UD Not Started', 0))
        col7.metric('On Hold', metrics.get('Dropped / On Hold', 0))
        
        st.dataframe(summary, use_container_width=True)
    
    # Section 2: Two-Column Layout
    st.markdown("<div class='section-header'><h2>⏳ Project Aging & Delivery</h2></div>", unsafe_allow_html=True)
    col_left, col_right = st.columns(2)
    
    with col_left:
        st.markdown('**High Aging Projects (Top 10)**')
        if not st.session_state.report['aging'].empty:
            st.dataframe(st.session_state.report['aging'], use_container_width=True)
        else:
            st.info('No aging data available')
    
    with col_right:
        st.markdown('**Recent Delivery Highlights (Last 7 Days)**')
        if not st.session_state.report['delivery'].empty:
            st.dataframe(st.session_state.report['delivery'], use_container_width=True)
        else:
            st.info('No deliveries in the last 7 days')
    
    # Section 3: Top Risk Projects
    st.markdown("<div class='section-header'><h2>🚨 Top Risk Projects</h2></div>", unsafe_allow_html=True)
    if not st.session_state.report['risks'].empty:
        st.dataframe(st.session_state.report['risks'], use_container_width=True)
    else:
        st.info('No risk data available')
    
    # Section 4: Outlook for Next Week
    st.markdown("<div class='section-header'><h2>📅 Outlook for Next Week</h2></div>", unsafe_allow_html=True)
    if not st.session_state.report['outlook'].empty:
        st.dataframe(st.session_state.report['outlook'], use_container_width=True)
    else:
        st.info('No planned deliveries for next week')
    
    # Section 5: Executive Summary
    st.markdown("<div class='section-header'><h2>💡 Executive Summary</h2></div>", unsafe_allow_html=True)
    if st.session_state.report.get('bullets'):
        for bullet in st.session_state.report['bullets']:
            st.markdown(f'- {bullet}')
    else:
        st.info('No summary bullets available')

# ============================================================
# MULTI-AGENT FORM
# ============================================================

st.markdown("<div class='section-header'><h2>🤖 Ask the Smart WSR Agent</h2></div>", unsafe_allow_html=True)

def classify_prompt(prompt: str) -> str:
    text = prompt.lower()
    if any(word in text for word in ['revise', 'rewrite', 'polish', 'refresh', 'reword']):
        return 'revise'
    if any(word in text for word in ['summary', 'bullet', 'executive', 'highlight', 'insight']):
        return 'summary'
    if any(word in text for word in ['status report', 'weekly report', 'wsr', 'report']):
        return 'report'
    return 'rag'

with st.form(key='assistant_form'):
    prompt = st.text_area('Enter a question or request for the report', height=100)
    agent_mode = st.selectbox(
        'Choose an agent or leave on automatic routing',
        ['Automatic', 'RAG assistant', 'Generate summary bullets', 'Revise report bullets', 'Create status report']
    )
    submitted = st.form_submit_button('🚀 Run Agent', use_container_width=True)

if submitted:
    if not prompt:
        st.warning('Please enter a prompt before running the agent.')
    elif not api_key:
        st.warning('Please provide a Gemini API key in the sidebar.')
    elif st.session_state.report is None:
        st.warning('Please upload data first.')
    else:
        route = agent_mode if agent_mode != 'Automatic' else classify_prompt(prompt)
        
        if route == 'RAG assistant' or route == 'rag':
            with st.spinner('🔍 Retrieving context and generating answer...'):
                response = answer_question(st.session_state.report['raw'], prompt, api_key)
                st.success('✅ RAG Agent Response')
                st.write(response)
                st.session_state.chat_history.append(('RAG Assistant', prompt, response))
        
        elif route == 'Generate summary bullets' or route == 'summary':
            with st.spinner('📝 Generating summary bullets...'):
                bullets = generate_bullets(st.session_state.report, prompt, api_key)
                st.success('✅ Generated Summary Bullets')
                for bullet in bullets:
                    st.markdown(f'- {bullet}')
                st.session_state.report['bullets'] = bullets
                st.session_state.chat_history.append(('Summary Agent', prompt, '\n'.join(bullets)))
        
        elif route == 'Revise report bullets' or route == 'revise':
            with st.spinner('✏️ Revising report bullets...'):
                updated = revise_report(st.session_state.report, prompt)
                st.success('✅ Revised Report Bullets')
                for bullet in updated.get('bullets', []):
                    st.markdown(f'- {bullet}')
                st.session_state.report = updated
                st.session_state.chat_history.append(('Revise Agent', prompt, '\n'.join(updated.get('bullets', []))))
        
        elif route == 'Create status report' or route == 'report':
            with st.spinner('📊 Creating status report...'):
                bullets = generate_report_summary(st.session_state.report, prompt, api_key)
                st.success('✅ Status Report Summary')
                for bullet in bullets:
                    st.markdown(f'- {bullet}')
                st.session_state.report['bullets'] = bullets
                st.session_state.chat_history.append(('Report Agent', prompt, '\n'.join(bullets)))

# ============================================================
# CHAT HISTORY
# ============================================================

if st.session_state.chat_history:
    with st.expander('💬 Agent Conversation History', expanded=False):
        for agent, question, answer in st.session_state.chat_history[-10:]:
            st.markdown(f'**{agent}**: {question}')
            st.markdown(answer)
            st.markdown('---')

# ============================================================
# ADVANCED DATA FILTERING
# ============================================================

if st.session_state.report is not None:
    st.markdown("<div class='section-header'><h2>🔍 Advanced Data Filtering</h2></div>", unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns(3)
    
    raw_df = st.session_state.report['raw']
    
    with col1:
        status_col = next((c for c in raw_df.columns if 'status' in c.lower()), None)
        status_options = raw_df[status_col].unique().tolist() if status_col else []
        status_filter = st.multiselect('Filter by Status', options=status_options, default=[])
    
    with col2:
        project_col = next((c for c in raw_df.columns if 'project' in c.lower()), None)
        project_filter = st.text_input('Filter by Project Name (partial match)')
    
    with col3:
        aging_min = st.number_input('Min Aging Days', min_value=0, value=0)
    
    if st.button('Apply Filters', use_container_width=True):
        filtered = raw_df.copy()
        
        if status_col and status_filter:
            filtered = filtered[filtered[status_col].isin(status_filter)]
        
        if project_col and project_filter:
            filtered = filtered[filtered[project_col].str.contains(project_filter, case=False, na=False)]
        
        if aging_min > 0 and 'Aging' in filtered.columns:
            filtered = filtered[filtered['Aging'] >= aging_min]
        
        st.session_state.filtered_df = filtered
        st.success(f'✅ Filtered to {len(filtered)} rows')
        st.dataframe(filtered.head(20), use_container_width=True)

# ============================================================
# EXPORT FUNCTIONS
# ============================================================

if st.session_state.report is not None:
    st.markdown("<div class='section-header'><h2>💾 Export Report</h2></div>", unsafe_allow_html=True)
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        if st.button('📄 Export to PDF', use_container_width=True):
            with st.spinner('Generating PDF...'):
                pdf_path = export_pdf(st.session_state.report)
                with open(pdf_path, 'rb') as f:
                    st.download_button('Download PDF', f, file_name='WSR_Report.pdf', mime='application/pdf')
                st.success('✅ PDF generated')
    
    with col2:
        if st.button('🎨 Export to PowerPoint', use_container_width=True):
            with st.spinner('Generating PowerPoint...'):
                ppt_path = export_ppt(st.session_state.report)
                with open(ppt_path, 'rb') as f:
                    st.download_button('Download PPT', f, file_name='WSR_Report.pptx', mime='application/vnd.openxmlformats-officedocument.presentationml.presentation')
                st.success('✅ PowerPoint generated')
    
    with col3:
        if st.button('🖼️ Export to Image', use_container_width=True):
            with st.spinner('Generating Image...'):
                png_path = export_png(st.session_state.report)
                with open(png_path, 'rb') as f:
                    st.download_button('Download PNG', f, file_name='WSR_Report.png', mime='image/png')
                st.success('✅ Image generated')
    
    with col4:
        filtered_df = st.session_state.filtered_df if st.session_state.filtered_df is not None else st.session_state.report['raw']
        csv_data = filtered_df.to_csv(index=False)
        st.download_button('📊 Download CSV', csv_data, file_name='filtered_data.csv', mime='text/csv', use_container_width=True)

# ============================================================
# EMAIL SENDING
# ============================================================

if st.session_state.report is not None:
    st.markdown("<div class='section-header'><h2>📧 Send Report via Email</h2></div>", unsafe_allow_html=True)
    
    col1, col2 = st.columns([3, 1])
    
    with col1:
        email_recipients = st.text_input(
            'Recipient Email(s)',
            placeholder='example@domain.com or email1@domain.com, email2@domain.com'
        )
    
    with col2:
        export_type = st.selectbox('Attachment Type', ['PDF', 'PowerPoint', 'PNG', 'CSV'])
    
    if st.button('Send Email', use_container_width=True):
        if not email_recipients:
            st.warning('Please enter recipient email address.')
        elif not st.session_state.smtp_settings['user'] or not st.session_state.smtp_settings['pass']:
            st.warning('Please configure SMTP settings in the sidebar.')
        else:
            try:
                with st.spinner('Sending email...'):
                    # Generate export
                    if export_type == 'PDF':
                        attachment_path = export_pdf(st.session_state.report)
                        filename = 'WSR_Report.pdf'
                    elif export_type == 'PowerPoint':
                        attachment_path = export_ppt(st.session_state.report)
                        filename = 'WSR_Report.pptx'
                    elif export_type == 'PNG':
                        attachment_path = export_png(st.session_state.report)
                        filename = 'WSR_Report.png'
                    else:
                        filtered_df = st.session_state.filtered_df if st.session_state.filtered_df is not None else st.session_state.report['raw']
                        attachment_path = f'/tmp/filtered_data.csv'
                        filtered_df.to_csv(attachment_path, index=False)
                        filename = 'filtered_data.csv'
                    
                    # Send email
                    msg = MIMEMultipart()
                    msg['From'] = st.session_state.smtp_settings['sender']
                    msg['To'] = email_recipients
                    msg['Subject'] = f"Weekly Status Report - {datetime.now().strftime('%Y-%m-%d')}"
                    
                    body = "Please find attached the Weekly Status Report."
                    msg.attach(MIMEText(body, 'plain'))
                    
                    with open(attachment_path, 'rb') as attachment:
                        part = MIMEBase('application', 'octet-stream')
                        part.set_payload(attachment.read())
                        encoders.encode_base64(part)
                        part.add_header('Content-Disposition', f'attachment; filename= {filename}')
                        msg.attach(part)
                    
                    with smtplib.SMTP(st.session_state.smtp_settings['host'], st.session_state.smtp_settings['port']) as server:
                        server.starttls()
                        server.login(st.session_state.smtp_settings['user'], st.session_state.smtp_settings['pass'])
                        server.send_message(msg)
                    
                    st.success(f'✅ Email sent successfully to {email_recipients}')
            except Exception as e:
                st.error(f'❌ Failed to send email: {e}')

# ============================================================
# PROJECT SEARCH
# ============================================================

if st.session_state.report is not None:
    st.markdown("<div class='section-header'><h2>🔎 Project Search</h2></div>", unsafe_allow_html=True)
    
    search_query = st.text_input('Search for project or module')
    
    if st.button('Search Projects', use_container_width=True):
        if not search_query.strip():
            st.warning('Please enter a search term.')
        else:
            raw_df = st.session_state.report['raw']
            project_col = next((c for c in raw_df.columns if 'project' in c.lower()), None)
            
            if project_col:
                results = raw_df[raw_df[project_col].str.contains(search_query, case=False, na=False)]
                if not results.empty:
                    st.success(f'Found {len(results)} matching project(s)')
                    st.dataframe(results, use_container_width=True)
                    
                    # Show detailed info for first result
                    st.markdown('**Project Details**')
                    for col in results.columns:
                        st.markdown(f'- **{col}**: {results.iloc[0][col]}')
                else:
                    st.info('No matching projects found.')
            else:
                st.warning('Project column not found in data.')

# ============================================================
# FOOTER
# ============================================================

st.markdown('---')
st.caption('Smart WSR Multi-Agent RAG app: Upload project status data, ask questions via RAG, or generate/revise AI-powered summary bullets using multiple specialized agents. Features comprehensive reporting, filtering, and export capabilities.')
