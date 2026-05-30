"""
Inicialização do cliente Supabase.
Usa psycopg2 via Session Pooler (IPv4) para contornar problema de DNS no Streamlit Cloud.
"""
import os
import streamlit as st
from supabase import create_client, Client
from dotenv import load_dotenv

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

        # Força uso do Session Pooler (IPv4) substituindo o host na URL
        # O Session Pooler resolve o problema de DNS do Streamlit Cloud
        pooler_url = url.replace(
            "xcqnoadgdhzwttvwqlir.supabase.co",
            "aws-1-sa-east-1.pooler.supabase.com"
        )

        st.session_state.supabase_client = create_client(pooler_url, key)

    return st.session_state.supabase_client
