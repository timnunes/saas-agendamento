"""
Dashboard principal — visão geral do negócio.
Mostra KPIs: agendamentos de hoje, semana, clientes, faturamento e próximo agendamento.
"""

import streamlit as st
from datetime import datetime, timedelta, timezone, date
from components.styles import injetar_css
from components.cards import card_metrica
from config.supabase_client import get_supabase

BR_TZ = timezone(timedelta(hours=-3))


def mostrar():
    injetar_css()
    st.title("📊 Dashboard")

    sb = get_supabase()
    empresa_id = st.session_state.empresa_id

    hoje = datetime.now(BR_TZ).date()
    inicio_semana = hoje - timedelta(days=hoje.weekday())
    fim_semana = inicio_semana + timedelta(days=6)
    inicio_mes = hoje.replace(day=1)

    # Datas em formato ISO com fuso horário para queries
    hoje_ini = datetime(hoje.year, hoje.month, hoje.day, 0, 0, 0, tzinfo=BR_TZ).isoformat()
    hoje_fim = datetime(hoje.year, hoje.month, hoje.day, 23, 59, 59, tzinfo=BR_TZ).isoformat()
    semana_ini = datetime(inicio_semana.year, inicio_semana.month, inicio_semana.day, 0, 0, 0, tzinfo=BR_TZ).isoformat()
    semana_fim = datetime(fim_semana.year, fim_semana.month, fim_semana.day, 23, 59, 59, tzinfo=BR_TZ).isoformat()
    mes_ini = datetime(inicio_mes.year, inicio_mes.month, inicio_mes.day, 0, 0, 0, tzinfo=BR_TZ).isoformat()

    try:
        # Agendamentos de hoje (não cancelados)
        resp_hoje = (
            sb.table("agd_agendamentos")
            .select("id")
            .eq("empresa_id", empresa_id)
            .gte("data_hora_inicio", hoje_ini)
            .lte("data_hora_inicio", hoje_fim)
            .neq("status", "cancelado")
            .execute()
        )
        total_hoje = len(resp_hoje.data) if resp_hoje.data else 0

        # Agendamentos desta semana (não cancelados)
        resp_semana = (
            sb.table("agd_agendamentos")
            .select("id")
            .eq("empresa_id", empresa_id)
            .gte("data_hora_inicio", semana_ini)
            .lte("data_hora_inicio", semana_fim)
            .neq("status", "cancelado")
            .execute()
        )
        total_semana = len(resp_semana.data) if resp_semana.data else 0

        # Total de clientes
        resp_clientes = (
            sb.table("agd_clientes")
            .select("id", count="exact")
            .eq("empresa_id", empresa_id)
            .execute()
        )
        total_clientes = resp_clientes.count if resp_clientes.count is not None else 0

        # Faturamento do mês (serviços concluídos)
        resp_fat = (
            sb.table("agd_agendamentos")
            .select("agd_servicos(preco)")
            .eq("empresa_id", empresa_id)
            .eq("status", "concluido")
            .gte("data_hora_inicio", mes_ini)
            .execute()
        )
        faturamento = sum(
            (a.get("agd_servicos") or {}).get("preco") or 0
            for a in (resp_fat.data or [])
        )

        # Clientes para retornar esta semana
        resp_retencao = (
            sb.table("agd_agendamentos")
            .select("id")
            .eq("empresa_id", empresa_id)
            .gte("data_retorno_sugerida", str(hoje))
            .lte("data_retorno_sugerida", str(fim_semana))
            .execute()
        )
        total_retencao = len(resp_retencao.data) if resp_retencao.data else 0

        # Próximo agendamento
        resp_proximo = (
            sb.table("agd_agendamentos")
            .select("data_hora_inicio, agd_clientes(nome), agd_servicos(nome)")
            .eq("empresa_id", empresa_id)
            .in_("status", ["pendente", "confirmado"])
            .gte("data_hora_inicio", datetime.now(BR_TZ).isoformat())
            .order("data_hora_inicio")
            .limit(1)
            .execute()
        )

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

    if resp_proximo.data:
        p = resp_proximo.data[0]
        dt = datetime.fromisoformat(p["data_hora_inicio"])
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        dt_br = dt.astimezone(BR_TZ)

        nome_cliente = (p.get("agd_clientes") or {}).get("nome", "—")
        nome_servico = (p.get("agd_servicos") or {}).get("nome", "—")

        st.info(
            f"**{nome_cliente}** — {nome_servico} às **{dt_br.strftime('%H:%M')}** "
            f"({dt_br.strftime('%d/%m/%Y')})"
        )
    else:
        st.info("Nenhum agendamento futuro encontrado.")
