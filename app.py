"""
AgendaPro — SaaS de Agendamento para Salões de Beleza
Entry point principal.

Lógica de roteamento:
  - URL com ?slug=nome-do-salao → página pública de agendamento (sem login)
  - URL sem slug → painel administrativo (requer login)
"""

import streamlit as st

st.set_page_config(
    page_title="AgendaPro — Salões",
    page_icon="✂️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ===== DEBUG TEMPORÁRIO — REMOVER APÓS RESOLVER =====
with st.expander("🔍 DEBUG — Secrets (remover após resolver)", expanded=True):
    st.subheader("Conteúdo de st.secrets")
    try:
        secrets_dict = dict(st.secrets)
        if secrets_dict:
            for chave, valor in secrets_dict.items():
                valor_str = str(valor)
                resumo = valor_str[:30] + "..." if len(valor_str) > 30 else valor_str
                st.write(f"**{chave}** → `{resumo}`")
        else:
            st.error("❌ st.secrets está VAZIO")
    except Exception as e:
        st.error(f"Erro ao ler st.secrets: {e}")

    st.subheader("Teste direto: DATABASE_URL")
    try:
        db_url = st.secrets["DATABASE_URL"]
        resumo = db_url[:40] + "..." if len(db_url) > 40 else db_url
        st.success(f"✅ Encontrada: `{resumo}`")
    except KeyError:
        st.error("❌ Chave DATABASE_URL não encontrada")
    except Exception as e:
        st.error(f"Erro: {e}")

    st.subheader("Teste de conexão PostgreSQL")
    try:
        import psycopg2
        db_url = st.secrets["DATABASE_URL"]
        conn = psycopg2.connect(db_url, connect_timeout=10)
        conn.close()
        st.success("✅ Conexão com o banco OK!")
    except KeyError:
        st.warning("⏭️ Pulando — DATABASE_URL não encontrada")
    except Exception as e:
        st.error(f"❌ Falha na conexão: {e}")
# ===== FIM DO DEBUG =====

from auth.login import mostrar_login

# ===== VERIFICAR SE É PÁGINA PÚBLICA =====
params = st.query_params
slug = params.get("slug", None)

if slug:
    from public.agendamento import mostrar_agendamento
    mostrar_agendamento(slug)

else:
    # ===== ÁREA ADMINISTRATIVA — REQUER LOGIN =====
    if "user" not in st.session_state:
        mostrar_login()
    else:
        from pages import dashboard, agenda, servicos, clientes
        from pages import bloqueios, lembretes, retencao, configuracoes
        from components.sidebar import montar_sidebar

        montar_sidebar()

        paginas = [
            st.Page(dashboard.mostrar,      title="Dashboard",     icon="📊", url_path="dashboard"),
            st.Page(agenda.mostrar,         title="Agenda",        icon="📅", url_path="agenda"),
            st.Page(servicos.mostrar,       title="Serviços",      icon="✂️", url_path="servicos"),
            st.Page(clientes.mostrar,       title="Clientes",      icon="👥", url_path="clientes"),
            st.Page(bloqueios.mostrar,      title="Bloqueios",     icon="🚫", url_path="bloqueios"),
            st.Page(lembretes.mostrar,      title="Lembretes",     icon="🔔", url_path="lembretes"),
            st.Page(retencao.mostrar,       title="Retenção",      icon="🔄", url_path="retencao"),
            st.Page(configuracoes.mostrar,  title="Configurações", icon="⚙️", url_path="configuracoes"),
        ]
        pg = st.navigation(paginas)
        pg.run()
