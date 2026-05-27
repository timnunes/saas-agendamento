"""
Inicialização do cliente Supabase.

IMPORTANTE:
- NÃO usar @st.cache_resource — causa bugs quando usuários diferentes fazem login
- O cliente é criado uma vez por sessão e reutilizado via st.session_state
- Usar .strip() nas variáveis de ambiente para evitar espaços acidentais
"""

import os
from supabase import create_client, Client
from dotenv import load_dotenv
import streamlit as st

load_dotenv()


def get_supabase() -> Client:
    """
    Retorna o cliente Supabase da sessão atual.
    Cria um novo cliente se ainda não existir na sessão.
    """
    if "supabase_client" not in st.session_state:
        url = os.environ.get("SUPABASE_URL", "").strip()
        key = os.environ.get("SUPABASE_ANON_KEY", "").strip()

        if not url or not key:
            st.error("❌ Variáveis SUPABASE_URL e SUPABASE_ANON_KEY não configuradas.")
            st.stop()

        st.session_state.supabase_client = create_client(url, key)

    return st.session_state.supabase_client
