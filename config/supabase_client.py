"""
Inicialização do cliente Supabase usando st_supabase_connection.
Biblioteca oficial recomendada pelo Streamlit para conexão com Supabase.
"""
import streamlit as st
from st_supabase_connection import SupabaseConnection


def get_supabase():
    if "supabase_client" not in st.session_state:
        conn = st.connection(
            name="supabase_connection",
            type=SupabaseConnection,
        )
        st.session_state.supabase_client = conn.client
    return st.session_state.supabase_client
