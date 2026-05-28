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

st.write(dict(st.secrets)) #debug temporario remover depois

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
