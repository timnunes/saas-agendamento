"""
Tela de login e logout do painel administrativo.
Autenticação via banco de dados (agd_perfis + agd_empresas).
Não usa Supabase Auth — verifica email e senha diretamente pelo banco.
"""

import streamlit as st
import bcrypt
import traceback
from config.supabase_client import get_db_conn


def _verificar_senha(senha_digitada: str, senha_hash: str) -> bool:
    try:
        return bcrypt.checkpw(senha_digitada.encode(), senha_hash.encode())
    except Exception:
        return False


def mostrar_login():
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

            try:
                conn = get_db_conn()
                cur = conn.cursor()
                cur.execute("""
                    SELECT
                        p.empresa_id,
                        p.nome AS perfil_nome,
                        e.nome AS empresa_nome,
                        e.slug,
                        e.cor_primaria,
                        e.senha_hash,
                        e.email
                    FROM agd_perfis p
                    JOIN agd_empresas e ON e.id = p.empresa_id
                    WHERE LOWER(e.email) = LOWER(%s)
                    LIMIT 1
                """, (email.strip(),))
                row = cur.fetchone()
                cur.close()

                if not row:
                    st.error("Email ou senha incorretos.")
                    return

                senha_hash = row.get("senha_hash", "")

                if not senha_hash:
                    st.error("Senha não configurada. Contate o suporte.")
                    return

                if not _verificar_senha(senha, senha_hash):
                    st.error("Email ou senha incorretos.")
                    return

                st.session_state.user         = {"email": email, "id": row["empresa_id"]}
                st.session_state.empresa_id   = row["empresa_id"]
                st.session_state.empresa_nome = row["empresa_nome"] or ""
                st.session_state.empresa_slug = row["slug"] or ""
                st.session_state.empresa_cor  = row["cor_primaria"] or "#8B5CF6"

                st.rerun()

            except Exception as e:
                st.error(f"Erro ao fazer login: {e}")
                st.code(traceback.format_exc())


def fazer_logout():
    for chave in list(st.session_state.keys()):
        del st.session_state[chave]
    st.rerun()
