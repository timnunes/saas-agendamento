"""
Inicialização do cliente Supabase.
Padrão idêntico ao dos outros apps que funcionam no Streamlit Cloud.
"""
import os
from supabase import create_client, Client
from dotenv import load_dotenv
import streamlit as st

load_dotenv()

def get_supabase() -> Client:
    if "supabase_client" not in st.session_state:
        try:
            url = st.secrets["SUPABASE_URL"].strip()
            key = st.secrets["SUPABASE_KEY"].strip()
        except Exception:
            url = os.environ.get("SUPABASE_URL", "").strip()
            key = os.environ.get("SUPABASE_ANON_KEY", "").strip()

        if not url or not key:
            st.error("❌ Credenciais não configuradas.")
            st.stop()

        st.session_state.supabase_client = create_client(url, key)

    return st.session_state.supabase_client
