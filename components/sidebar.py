"""
Sidebar com informações do salão e botão de logout.
"""
import streamlit as st
from auth.login import fazer_logout


def montar_sidebar():
    with st.sidebar:
        empresa_nome = st.session_state.get("empresa_nome", "AgendaPro")
        st.markdown(
            f'<div class="empresa-nome-sidebar">✂️ {empresa_nome}</div>',
            unsafe_allow_html=True,
        )
        st.divider()

        st.markdown("<br>" * 2, unsafe_allow_html=True)

        if st.button("🚪 Sair", use_container_width=True):
            fazer_logout()
