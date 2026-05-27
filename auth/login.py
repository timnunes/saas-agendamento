"""
Tela de login e logout do painel administrativo.
Usa Supabase Auth com email e senha.
"""

import streamlit as st
from config.supabase_client import get_supabase


def mostrar_login():
    """Renderiza a tela de login."""
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("## ✂️ AgendaPro")
        st.markdown("**Sistema de Agendamento para Salões de Beleza**")
        st.divider()

        with st.form("form_login", clear_on_submit=False):
            st.subheader("Acesse sua conta")
            email = st.text_input("📧 Email", placeholder="seu@email.com")
            senha = st.text_input("🔒 Senha", type="password", placeholder="••••••••")
            entrar = st.form_submit_button("Entrar", use_container_width=True, type="primary")

        if entrar:
            if not email or not senha:
                st.error("Preencha email e senha.")
                return

            sb = get_supabase()
            try:
                resp = sb.auth.sign_in_with_password({"email": email, "password": senha})
                user = resp.user

                if not user:
                    st.error("Email ou senha incorretos.")
                    return

                # Buscar empresa vinculada ao usuário
                perfil = (
                    sb.table("agd_perfis")
                    .select("empresa_id, nome")
                    .eq("user_id", str(user.id))
                    .execute()
                )
                if not perfil.data:
                    st.error("Conta sem empresa vinculada. Contate o suporte.")
                    return

                empresa_id = perfil.data[0]["empresa_id"]

                # Buscar dados da empresa
                empresa_resp = (
                    sb.table("agd_empresas")
                    .select("nome, slug, cor_primaria")
                    .eq("id", empresa_id)
                    .execute()
                )
                empresa_nome = ""
                empresa_slug = ""
                empresa_cor  = "#8B5CF6"
                if empresa_resp.data:
                    empresa_nome = empresa_resp.data[0]["nome"]
                    empresa_slug = empresa_resp.data[0]["slug"]
                    empresa_cor  = empresa_resp.data[0].get("cor_primaria", "#8B5CF6")

                # Salvar na sessão
                st.session_state.user         = user
                st.session_state.empresa_id   = empresa_id
                st.session_state.empresa_nome = empresa_nome
                st.session_state.empresa_slug = empresa_slug
                st.session_state.empresa_cor  = empresa_cor

                st.rerun()

            except Exception as e:
                mensagem = str(e)
                if "Invalid login credentials" in mensagem:
                    st.error("Email ou senha incorretos.")
                else:
                    st.error(f"Erro ao fazer login: {mensagem}")


def fazer_logout():
    """Faz logout do usuário e limpa a sessão."""
    sb = get_supabase()
    try:
        sb.auth.sign_out()
    except Exception:
        pass

    for chave in list(st.session_state.keys()):
        del st.session_state[chave]

    st.rerun()
