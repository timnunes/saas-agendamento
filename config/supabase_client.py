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
    """Cria o cliente Supabase uma única vez e reutiliza em todas as sessões."""
    # Tenta st.secrets primeiro (Streamlit Cloud)
    try:
        url = st.secrets.get("SUPABASE_URL", "").strip()
        # Aceita tanto SUPABASE_KEY quanto SUPABASE_ANON_KEY
        key = st.secrets.get("SUPABASE_KEY", "") or st.secrets.get("SUPABASE_ANON_KEY", "")
        key = key.strip()
    except Exception:
        url = ""
        key = ""

    # Fallback para variáveis de ambiente (.env local)
    if not url:
        url = os.environ.get("SUPABASE_URL", "").strip()
    if not key:
        key = os.environ.get("SUPABASE_ANON_KEY", "").strip()

    if not url or not key:
        st.error("❌ Variáveis SUPABASE_URL e SUPABASE_KEY não configuradas.")
        st.stop()

    return create_client(url, key)


def get_supabase() -> Client:
    """Retorna o cliente Supabase cacheado."""
    return _init_supabase()
