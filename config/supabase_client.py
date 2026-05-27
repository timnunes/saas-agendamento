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
        url = ""
        key = ""

        # Tenta st.secrets primeiro (Streamlit Cloud)
        try:
            url = st.secrets.get("SUPABASE_URL", "").strip()
            key = st.secrets.get("SUPABASE_ANON_KEY", "").strip()
        except Exception:
            pass

        # Se não veio do secrets, tenta variável de ambiente (.env local)
        if not url:
            url = os.environ.get("SUPABASE_URL", "").strip()
        if not key:
            key = os.environ.get("SUPABASE_ANON_KEY", "").strip()

        if not url or not key:
            st.error("❌ Variáveis SUPABASE_URL e SUPABASE_ANON_KEY não configuradas.")
            st.stop()

        try:
            st.session_state.supabase_client = create_client(url, key)
        except Exception as e:
            st.error(f"❌ Erro ao conectar no Supabase: {e}")
            st.error(f"URL usada: {url[:50]}...")
            st.stop()

    return st.session_state.supabase_client
