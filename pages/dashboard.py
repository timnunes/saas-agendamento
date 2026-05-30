"""
Dashboard principal — visão geral do negócio.
Mostra KPIs: agendamentos de hoje, semana, clientes, faturamento e próximo agendamento.
"""

import streamlit as st
from datetime import datetime, timedelta, timezone
from components.styles import injetar_css
from components.cards import card_metrica
from config.supabase_client import get_db_conn

BR_TZ = timezone(timedelta(hours=-3))


def mostrar():
    injetar_css()
    st.title("📊 Dashboard")

    conn = get_db_conn()
    empresa_id = st.session_state.empresa_id

    hoje = datetime.now(BR_TZ).date()
    inicio_semana = hoje - timedelta(days=hoje.weekday())
    fim_semana = inicio_semana + timedelta(days=6)
    inicio_mes = hoje.replace(day=1)

    hoje_ini = datetime(hoje.year, hoje.month, hoje.day, 0, 0, 0, tzinfo=BR_TZ).isoformat()
    hoje_fim = datetime(hoje.year, hoje.month, hoje.day, 23, 59, 59, tzinfo=BR_TZ).isoformat()
    semana_ini = datetime(inicio_semana.year, inicio_semana.month, inicio_semana.day, 0, 0, 0, tzinfo=BR_TZ).isoformat()
    semana_fim = datetime(fim_semana.year, fim_semana.month, fim_semana.day, 23, 59, 59, tzinfo=BR_TZ).isoformat()
    mes_ini = datetime(inicio_mes.year, inicio_mes.month, inicio_mes.day, 0, 0, 0, tzinfo=BR_TZ).isoformat()

    try:
        cur = conn.cursor()

        # Agendamentos de hoje (não cancelados)
        cur.execute("""
            SELECT COUNT(*) FROM agd_agendamentos
            WHERE empresa_id = %s
              AND status != 'cancelado'
              AND data_hora_inicio >= %s
              AND data_hora_inicio <= %s
        """, (empresa_id, hoje_ini, hoje_fim))
        total_hoje = cur.fetchone()["count"]

        # Agendamentos desta semana (não cancelados)
        cur.execute("""
            SELECT COUNT(*) FROM agd_agendamentos
            WHERE empresa_id = %s
              AND status != 'cancelado'
              AND data_hora_inicio >= %s
              AND data_hora_inicio <= %s
        """, (empresa_id, semana_ini, semana_fim))
        total_semana = cur.fetchone()["count"]

        # Total de clientes
        cur.execute("""
            SELECT COUNT(*) FROM agd_clientes
            WHERE empresa_id = %s
        """, (empresa_id,))
        total_clientes = cur.fetchone()["count"]

        # Faturamento do mês (serviços concluídos)
        cur.execute("""
            SELECT COALESCE(SUM(s.preco), 0) AS total
            FROM agd_agendamentos a
            JOIN agd_servicos s ON s.id = a.servico_id
            WHERE a.empresa_id = %s
              AND a.status = 'concluido'
              AND a.data_hora_inicio >= %s
        """, (empresa_id, mes_ini))
        faturamento = float(cur.fetchone()["total"] or 0)

        # Clientes para retornar esta semana
        cur.execute("""
            SELECT COUNT(*) FROM agd_agendamentos
            WHERE empresa_id = %s
              AND data_retorno_sugerida >= %s
              AND data_retorno_sugerida <= %s
        """, (empresa_id, str(hoje), str(fim_semana)))
        total_retencao = cur.fetchone()["count"]

        # Próximo agendamento
        cur.execute("""
            SELECT a.data_hora_inicio, c.nome AS cliente_nome, s.nome AS servico_nome
            FROM agd_agendamentos a
            JOIN agd_clientes c ON c.id = a.cliente_id
            JOIN agd_servicos s ON s.id = a.servico_id
            WHERE a.empresa_id = %s
              AND a.status IN ('pendente', 'confirmado')
              AND a.data_hora_inicio >= %s
            ORDER BY a.data_hora_inicio ASC
            LIMIT 1
        """, (empresa_id, datetime.now(BR_TZ).isoformat()))
        proximo = cur.fetchone()

        cur.close()

    except Exception as e:
        st.error(f"Erro ao carregar dados do dashboard: {e}")
        return

    # ===== CARDS KPI =====
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        card_metrica("Agendamentos hoje", str(total_hoje), "📅")
    with col2:
        card_metrica("Esta semana", str(total_semana), "📆", "#3B82F6")
    with col3:
        card_metrica("Total de clientes", str(total_clientes), "👥", "#10B981")
    with col4:
        fat_fmt = f"R$ {faturamento:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        card_metrica("Faturamento do mês", fat_fmt, "💰", "#F59E0B")

    col5, col6 = st.columns([1, 3])
    with col5:
        card_metrica("Retornar esta semana", str(total_retencao), "🔄", "#EF4444")

    # ===== PRÓXIMO AGENDAMENTO =====
    st.divider()
    st.subheader("⏰ Próximo Agendamento")

    if proximo:
        dt = datetime.fromisoformat(str(proximo["data_hora_inicio"]))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        dt_br = dt.astimezone(BR_TZ)

        st.info(
            f"**{proximo['cliente_nome']}** — {proximo['servico_nome']} às "
            f"**{dt_br.strftime('%H:%M')}** ({dt_br.strftime('%d/%m/%Y')})"
        )
    else:
        st.info("Nenhum agendamento futuro encontrado.")