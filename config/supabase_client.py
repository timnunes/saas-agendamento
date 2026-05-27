"""
Inicialização do cliente Supabase.
Lê credenciais de st.secrets (Streamlit Cloud) ou .env (local).
"""
import os
from supabase import create_client, Client
from dotenv import load_dotenv
import streamlit as st

load_dotenv()

def get_supabase() -> Client:
    if "supabase_client" not in st.session_state:
        # Tenta st.secrets primeiro (Streamlit Cloud)
        # Se não encontrar, cai para variáveis de ambiente (.env local)
        try:
            url = st.secrets["SUPABASE_URL"].strip()
            key = st.secrets["SUPABASE_ANON_KEY"].strip()
        except Exception:
            url = os.environ.get("SUPABASE_URL", "").strip()
            key = os.environ.get("SUPABASE_ANON_KEY", "").strip()

        if not url or not key:
            st.error("❌ Variáveis SUPABASE_URL e SUPABASE_ANON_KEY não configuradas.")
            st.stop()

        st.session_state.supabase_client = create_client(url, key)
    return st.session_state.supabase_client
