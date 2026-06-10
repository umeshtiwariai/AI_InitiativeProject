import streamlit as st

def apply_theme():
    st.markdown('''
    <style>
    .stApp {background: linear-gradient(180deg,#fff7fb,#f8f0ff);}
    div[data-testid="stMetric"] {background:white;padding:14px;border-radius:14px;border-left:6px solid #FF66CC;}
    </style>
    ''', unsafe_allow_html=True)