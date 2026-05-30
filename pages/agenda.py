"""
Agenda — listagem e gestão de agendamentos.
"""

import streamlit as st
from datetime import datetime, timedelta, timezone, date
from components.styles import injetar_css
from components.cards import badge_status
from config.supabase_client import get_supabase, get_db_conn

BR_TZ = timezone(timedelta(hours=-3))
ITENS_POR_PAGINA = 20

DIAS_PT = ["Segunda-feira", "Terça-feira", "Quarta-feira", "Quinta-feira", "Sexta-feira", "Sábado", "Domingo"]
MESES_PT = ["janeiro", "fevereiro", "março", "abril", "maio", "junho", "julho",
            "agosto", "setembro", "outubro", "novembro", "dezembro"]


def _fmt_dt(iso_str):
    dt = datetime.fromisoformat(iso_str)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(BR_TZ).strftime("%H:%M")


def _fmt_data(iso_str):
    dt = datetime.fromisoformat(iso_str)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(BR_TZ).strftime("%d/%m/%Y")


def _fmt_data_hora(iso_str):
    dt = datetime.fromisoformat(iso_str)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(BR_TZ).strftime("%d/%m/%Y às %H:%M")


def _data_pt(d):
    return f"{DIAS_PT[d.weekday()]}, {d.day:02d} de {MESES_PT[d.month-1]} de {d.year}"


def _mudar_status(conn, agend_id, novo_status, empresa_id):
    try:
        cur = conn.cursor()
        dados = {"status": novo_status}
        if novo_status == "concluido":
            cur.execute("""
                SELECT a.data_hora_inicio, s.retorno_dias
                FROM agd_agendamentos a
                JOIN agd_servicos s ON s.id = a.servico_id
                WHERE a.id = %s
            """, (agend_id,))
            row = cur.fetchone()
            if row and row["retorno_dias"]:
                dt = datetime.fromisoformat(str(row["data_hora_inicio"]))
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                data_retorno = str(dt.astimezone(BR_TZ).date() + timedelta(days=row["retorno_dias"]))
                cur.execute("""
                    UPDATE agd_agendamentos
                    SET status = %s, data_retorno_sugerida = %s
                    WHERE id = %s AND empresa_id = %s
                """, (novo_status, data_retorno, agend_id, empresa_id))
            else:
                cur.execute("""
                    UPDATE agd_agendamentos SET status = %s
                    WHERE id = %s AND empresa_id = %s
                """, (novo_status, agend_id, empresa_id))
        else:
            cur.execute("""
                UPDATE agd_agendamentos SET status = %s
                WHERE id = %s AND empresa_id = %s
            """, (novo_status, agend_id, empresa_id))
        cur.close()
        st.success("Status atualizado!")
        st.rerun()
    except Exception as e:
        st.error(f"Erro ao atualizar: {e}")


def _buscar_agendamentos(conn, empresa_id, inicio, fim, status_filtro=None):
    cur = conn.cursor()
    sql = """
        SELECT a.*, c.nome AS cliente_nome, c.telefone AS cliente_telefone,
               s.nome AS servico_nome, s.duracao_minutos, s.retorno_dias
        FROM agd_agendamentos a
        JOIN agd_clientes c ON c.id = a.cliente_id
        JOIN agd_servicos s ON s.id = a.servico_id
        WHERE a.empresa_id = %s
          AND a.data_hora_inicio >= %s
          AND a.data_hora_inicio <= %s
    """
    params = [empresa_id, inicio, fim]
    if status_filtro:
        sql += " AND a.status = %s"
        params.append(status_filtro)
    sql += " ORDER BY a.data_hora_inicio ASC"
    cur.execute(sql, params)
    rows = [dict(r) for r in cur.fetchall()]
    cur.close()
    # Normaliza para o formato esperado pelo _renderizar_agendamento
    for r in rows:
        r["agd_clientes"] = {"nome": r.pop("cliente_nome"), "telefone": r.pop("cliente_telefone")}
        r["agd_servicos"] = {"nome": r.pop("servico_nome"), "duracao_minutos": r["duracao_minutos"], "retorno_dias": r.get("retorno_dias")}
    return rows


def _renderizar_agendamento(conn, a, empresa_id, chave, mostrar_data=False):
    horario = _fmt_data_hora(a["data_hora_inicio"]) if mostrar_data else _fmt_dt(a["data_hora_inicio"])
    nome_cliente = (a.get("agd_clientes") or {}).get("nome", "—")
    nome_servico = (a.get("agd_servicos") or {}).get("nome", "—")
    duracao = (a.get("agd_servicos") or {}).get("duracao_minutos", 0)
    status = a.get("status", "pendente")
    obs = a.get("observacoes", "")

    icones_status = {"pendente": "⏳", "confirmado": "✅", "concluido": "✔️", "cancelado": "❌"}
    icone = icones_status.get(status, "•")

    col_hora, col_info, col_status = st.columns([2, 4, 1])
    with col_hora:
        st.markdown(f"**{horario}**")
    with col_info:
        st.markdown(f"**{nome_cliente}**")
        detalhe = f"{nome_servico} • {duracao} min"
        if obs:
            detalhe += f" • _{obs}_"
        st.caption(detalhe)
    with col_status:
        st.markdown(f"{icone} {status.capitalize()}")

    if status not in ("concluido", "cancelado"):
        col_a, col_b, col_c, _ = st.columns([1, 1, 1, 3])
        with col_a:
            if status == "pendente" and st.button("✅ Confirmar", key=f"conf_{chave}"):
                _mudar_status(conn, a["id"], "confirmado", empresa_id)
        with col_b:
            if st.button("✔️ Concluir", key=f"conc_{chave}"):
                _mudar_status(conn, a["id"], "concluido", empresa_id)
        with col_c:
            if st.button("❌ Cancelar", key=f"canc_{chave}"):
                _mudar_status(conn, a["id"], "cancelado", empresa_id)

    st.markdown("---")


def _novo_agendamento_admin(sb, conn, empresa_id, prefixo):
    contador_key = f"form_counter_{prefixo}"
    if contador_key not in st.session_state:
        st.session_state[contador_key] = 0
    contador = st.session_state[contador_key]

    with st.expander("➕ Novo Agendamento", expanded=False):
        servicos = sb.table("agd_servicos").select("id, nome, duracao_minutos").eq("empresa_id", empresa_id).eq("ativo", True).order("nome").execute().data or []
        if not servicos:
            st.warning("Nenhum serviço cadastrado. Cadastre um serviço primeiro.")
            return

        busca_cliente = st.text_input(
            "🔍 Buscar cliente por nome ou telefone",
            placeholder="Digite o nome ou telefone...",
            key=f"busca_cliente_{prefixo}_{contador}"
        )

        cliente_id = None
        cliente_nome_selecionado = None

        if busca_cliente.strip():
            try:
                resultado = (
                    sb.table("agd_clientes").select("id, nome, telefone")
                    .eq("empresa_id", empresa_id)
                    .or_(f"nome.ilike.%{busca_cliente}%,telefone.ilike.%{busca_cliente}%")
                    .order("nome").limit(10).execute().data or []
                )
            except Exception:
                resultado = []

            if not resultado:
                st.warning("Nenhum cliente encontrado.")
            else:
                opcoes = {f"{c['nome']} — {c['telefone']}": c for c in resultado}
                escolha = st.selectbox("Selecione o cliente", list(opcoes.keys()), key=f"sel_cliente_{prefixo}_{contador}")
                cliente_selecionado = opcoes[escolha]
                cliente_id = cliente_selecionado["id"]
                cliente_nome_selecionado = cliente_selecionado["nome"]
        else:
            st.caption("Digite o nome ou telefone do cliente para buscá-lo.")

        opcoes_servicos = {s["nome"]: s for s in servicos}
        col2, col3, col4 = st.columns(3)
        with col2:
            servico_nome = st.selectbox("Serviço", list(opcoes_servicos.keys()), key=f"novo_servico_{prefixo}_{contador}")
        with col3:
            data_ag = st.date_input("Data", value=datetime.now(BR_TZ).date(), key=f"novo_data_{prefixo}_{contador}", format="DD/MM/YYYY")
        with col4:
            hora_ag = st.time_input("Horário", key=f"novo_hora_{prefixo}_{contador}")

        obs = st.text_input("Observações (opcional)", key=f"novo_obs_{prefixo}_{contador}")

        recorrente = st.checkbox("🔁 Repetir semanalmente?", key=f"novo_recorr_{prefixo}_{contador}")
        semanas = 1
        if recorrente:
            semanas = st.slider("Repetir por quantas semanas?", min_value=2, max_value=26, value=8, step=1, key=f"novo_semanas_{prefixo}_{contador}")
            st.caption(f"Serão criados **{semanas} agendamentos** — de {data_ag.strftime('%d/%m/%Y')} até {(data_ag + timedelta(weeks=semanas-1)).strftime('%d/%m/%Y')} ({DIAS_PT[data_ag.weekday()]}s às {hora_ag.strftime('%H:%M')})")

        label_btn = f"💾 Salvar {semanas} agendamento(s)" if recorrente else "💾 Salvar Agendamento"
        if st.button(label_btn, key=f"novo_salvar_{prefixo}_{contador}"):
            if not cliente_id:
                st.error("Selecione um cliente antes de salvar.")
                return
            try:
                servico = opcoes_servicos[servico_nome]
                criados = 0
                conflitos_datas = []

                for semana in range(semanas):
                    data_atual = data_ag + timedelta(weeks=semana)
                    dt_inicio = datetime(data_atual.year, data_atual.month, data_atual.day,
                                        hora_ag.hour, hora_ag.minute, 0, tzinfo=BR_TZ)
                    dt_fim = dt_inicio + timedelta(minutes=servico["duracao_minutos"])

                    conflito = sb.table("agd_agendamentos").select("id")\
                        .eq("empresa_id", empresa_id).neq("status", "cancelado")\
                        .lt("data_hora_inicio", dt_fim.isoformat())\
                        .gt("data_hora_fim", dt_inicio.isoformat()).execute().data

                    if conflito:
                        conflitos_datas.append(data_atual.strftime("%d/%m/%Y"))
                        continue

                    sb.table("agd_agendamentos").insert({
                        "empresa_id": empresa_id,
                        "cliente_id": cliente_id,
                        "servico_id": servico["id"],
                        "data_hora_inicio": dt_inicio.isoformat(),
                        "data_hora_fim": dt_fim.isoformat(),
                        "status": "confirmado",
                        "observacoes": obs,
                    }).execute()
                    criados += 1

                if criados > 0:
                    st.success(f"✅ {criados} agendamento(s) criado(s) para {cliente_nome_selecionado}!")
                if conflitos_datas:
                    st.warning(f"⚠️ {len(conflitos_datas)} data(s) pulada(s) por conflito: {', '.join(conflitos_datas)}")
                if criados > 0:
                    st.session_state[contador_key] += 1
                    st.rerun()
            except Exception as e:
                st.error(f"Erro ao salvar: {e}")


def _aba_hoje(sb, conn, empresa_id):
    hoje = datetime.now(BR_TZ).date()
    inicio = datetime(hoje.year, hoje.month, hoje.day, 0, 0, 0, tzinfo=BR_TZ).isoformat()
    fim = datetime(hoje.year, hoje.month, hoje.day, 23, 59, 59, tzinfo=BR_TZ).isoformat()

    try:
        agendamentos = _buscar_agendamentos(conn, empresa_id, inicio, fim)
    except Exception as e:
        st.error(f"Erro ao buscar agendamentos: {e}")
        return

    st.markdown(f"**{_data_pt(hoje)}**")
    st.caption(f"{len(agendamentos)} agendamento(s) hoje")
    _novo_agendamento_admin(sb, conn, empresa_id, "hoje")

    if not agendamentos:
        st.info("Nenhum agendamento para hoje.")
        return

    for i, a in enumerate(agendamentos):
        _renderizar_agendamento(conn, a, empresa_id, f"hoje_{i}_{a['id'][:8]}")


def _aba_semana(sb, conn, empresa_id):
    hoje = datetime.now(BR_TZ).date()
    inicio_semana_default = hoje - timedelta(days=hoje.weekday())

    col1, col2 = st.columns([3, 2])
    with col1:
        data_ref = st.date_input("Semana de referência", value=inicio_semana_default, key="semana_ref", format="DD/MM/YYYY")

    inicio_semana = data_ref - timedelta(days=data_ref.weekday())
    fim_semana = inicio_semana + timedelta(days=6)

    with col2:
        st.caption(f"📅 {inicio_semana.strftime('%d/%m/%Y')} a {fim_semana.strftime('%d/%m/%Y')}")

    inicio = datetime(inicio_semana.year, inicio_semana.month, inicio_semana.day, 0, 0, 0, tzinfo=BR_TZ).isoformat()
    fim = datetime(fim_semana.year, fim_semana.month, fim_semana.day, 23, 59, 59, tzinfo=BR_TZ).isoformat()

    try:
        agendamentos = _buscar_agendamentos(conn, empresa_id, inicio, fim)
    except Exception as e:
        st.error(f"Erro ao buscar agendamentos: {e}")
        return

    _novo_agendamento_admin(sb, conn, empresa_id, "semana")

    por_dia = {}
    for a in agendamentos:
        dia = _fmt_data(a["data_hora_inicio"])
        por_dia.setdefault(dia, []).append(a)

    nomes_dias = ["Seg", "Ter", "Qua", "Qui", "Sex", "Sáb", "Dom"]
    for offset in range(7):
        d = inicio_semana + timedelta(days=offset)
        dia_fmt = d.strftime("%d/%m/%Y")
        lista = por_dia.get(dia_fmt, [])
        with st.expander(f"{nomes_dias[d.weekday()]} {dia_fmt} — {len(lista)} agendamento(s)", expanded=(d == hoje)):
            if not lista:
                st.caption("Sem agendamentos.")
            for i, a in enumerate(lista):
                _renderizar_agendamento(conn, a, empresa_id, f"sem_{dia_fmt}_{i}_{a['id'][:8]}")


def _aba_todos(sb, conn, empresa_id):
    hoje = datetime.now(BR_TZ).date()

    col1, col2, col3 = st.columns(3)
    with col1:
        filtro_status = st.selectbox("Status", ["Todos", "pendente", "confirmado", "concluido", "cancelado"], key="filtro_status")
    with col2:
        data_ini = st.date_input("De", value=hoje - timedelta(days=30), key="filtro_de", format="DD/MM/YYYY")
    with col3:
        data_fim_f = st.date_input("Até", value=hoje + timedelta(days=30), key="filtro_ate", format="DD/MM/YYYY")

    inicio = datetime(data_ini.year, data_ini.month, data_ini.day, 0, 0, 0, tzinfo=BR_TZ).isoformat()
    fim = datetime(data_fim_f.year, data_fim_f.month, data_fim_f.day, 23, 59, 59, tzinfo=BR_TZ).isoformat()
    status_filtro = None if filtro_status == "Todos" else filtro_status

    try:
        todos = _buscar_agendamentos(conn, empresa_id, inicio, fim, status_filtro)
    except Exception as e:
        st.error(f"Erro ao buscar agendamentos: {e}")
        return

    st.caption(f"{len(todos)} agendamento(s) encontrado(s)")

    total_paginas = max(1, (len(todos) + ITENS_POR_PAGINA - 1) // ITENS_POR_PAGINA)
    pagina = st.number_input("Página", min_value=1, max_value=total_paginas, value=1, step=1, key="pag_todos")
    inicio_idx = (pagina - 1) * ITENS_POR_PAGINA
    pagina_itens = todos[inicio_idx:inicio_idx + ITENS_POR_PAGINA]

    if not pagina_itens:
        st.info("Nenhum agendamento encontrado com esses filtros.")
        return

    for i, a in enumerate(pagina_itens):
        _renderizar_agendamento(conn, a, empresa_id, f"todos_{pagina}_{i}_{a['id'][:8]}", mostrar_data=True)


def mostrar():
    injetar_css()
    st.title("📅 Agenda")

    sb = get_supabase()
    conn = get_db_conn()
    empresa_id = st.session_state.empresa_id

    aba_hoje, aba_semana, aba_todos = st.tabs(["📆 Hoje", "🗓️ Semana", "📋 Todos"])

    with aba_hoje:
        _aba_hoje(sb, conn, empresa_id)
    with aba_semana:
        _aba_semana(sb, conn, empresa_id)
    with aba_todos:
        _aba_todos(sb, conn, empresa_id)
