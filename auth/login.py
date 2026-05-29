"""
Tela de login e logout do painel administrativo.
Autenticação via banco de dados (agd_perfis + agd_empresas).
Não usa Supabase Auth — verifica email e senha diretamente pelo banco.
"""

import streamlit as st
import bcrypt
from config.supabase_client import get_supabase


def _verificar_senha(senha_digitada: str, senha_hash: str) -> bool:
    """Verifica se a senha digitada corresponde ao hash armazenado."""
    try:
        return bcrypt.checkpw(senha_digitada.encode(), senha_hash.encode())
    except Exception:
        return False


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
                # Busca o perfil pelo email na tabela agd_perfis
                # join com agd_empresas para pegar a senha_hash
                perfil_resp = (
                    sb.table("agd_perfis")
                    .select("empresa_id, nome, agd_empresas(nome, slug, cor_primaria, senha_hash, email)")
                    .execute()
                )

                # Filtra pelo email
                perfil = None
                for p in (perfil_resp.data or []):
                    empresa = p.get("agd_empresas") or {}
                    if empresa.get("email", "").lower() == email.lower().strip():
                        perfil = p
                        break

                if not perfil:
                    st.error("Email ou senha incorretos.")
                    return

                empresa = perfil.get("agd_empresas") or {}
                senha_hash = empresa.get("senha_hash", "")

                if not senha_hash:
                    st.error("Senha não configurada. Contate o suporte.")
                    return

                if not _verificar_senha(senha, senha_hash):
                    st.error("Email ou senha incorretos.")
                    return

                # Login bem-sucedido — salva na sessão
                st.session_state.user         = {"email": email, "id": perfil["empresa_id"]}
                st.session_state.empresa_id   = perfil["empresa_id"]
                st.session_state.empresa_nome = empresa.get("nome", "")
                st.session_state.empresa_slug = empresa.get("slug", "")
                st.session_state.empresa_cor  = empresa.get("cor_primaria", "#8B5CF6")

                st.rerun()

                            
	    except Exception as e:
   		import traceback
                st.error(f"Erro ao fazer login: {e}")
                st.code(traceback.format_exc())


def fazer_logout():
    """Faz logout do usuário e limpa a sessão."""
    for chave in list(st.session_state.keys()):
        del st.session_state[chave]
    st.rerun()
