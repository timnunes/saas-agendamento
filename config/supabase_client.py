"""
Inicialização do cliente Supabase.
Usa st.cache_resource conforme documentação oficial do Streamlit.
Lê credenciais de st.secrets (Streamlit Cloud) ou .env (local).
"""
import os
from supabase import create_client, Client
from dotenv import load_dotenv
import streamlit as st

load_dotenv()

@st.cache_resource
def _init_supabase() -> Client:
    """Cria o cliente Supabase uma única vez e reutiliza."""
    try:
        url = st.secrets.get("SUPABASE_URL", "").strip()
        key = (st.secrets.get("SUPABASE_KEY", "") or st.secrets.get("SUPABASE_ANON_KEY", "")).strip()
    except Exception:
        url = ""
        key = ""

    if not url:
        url = os.environ.get("SUPABASE_URL", "").strip()
    if not key:
        key = os.environ.get("SUPABASE_ANON_KEY", "").strip()

    if not url or not key:
        st.error("❌ Variáveis SUPABASE_URL e SUPABASE_KEY não configuradas.")
        st.stop()

    return create_client(url, key)


def get_supabase() -> Client:
    return _init_supabase()
