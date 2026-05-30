"""
Inicialização do cliente Supabase.
Força IPv4 para resolver problema de DNS no Streamlit Cloud.
"""
import os
import socket
import httpx
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

        # Força resolução IPv4 para evitar problema de DNS no Streamlit Cloud
        transport = httpx.HTTPTransport(local_address="0.0.0.0")
        http_client = httpx.Client(transport=transport)

        client = create_client(url, key, options={"httpx_client": http_client})
        st.session_state.supabase_client = client

    return st.session_state.supabase_client
