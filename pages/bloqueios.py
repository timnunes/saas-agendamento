"""
Bloqueios de horários e dias.
"""

import streamlit as st
from datetime import date, datetime, timedelta, timezone
from components.styles import injetar_css
from config.supabase_client import get_supabase

BR_TZ = timezone(timedelta(hours=-3))

DIAS_SEMANA = {0: "Domingo", 1: "Segunda-feira", 2: "Terça-feira",
               3: "Quarta-feira", 4: "Quinta-feira", 5: "Sexta-feira", 6: "Sábado"}


def _criar_bloqueio(sb, empresa_id, dados):
    try:
        sb.table("agd_bloqueios").insert({**dados, "empresa_id": empresa_id}).execute()
        st.success("✅ Bloqueio criado com sucesso!")
        st.rerun()
    except Exception as e:
        st.error(f"Erro ao criar bloqueio: {e}")


def _excluir_bloqueio(sb, bloqueio_id, empresa_id):
    try:
        sb.table("agd_bloqueios").delete().eq("id", bloqueio_id).eq("empresa_id", empresa_id).execute()
        st.success("Bloqueio removido.")
        st.rerun()
    except Exception as e:
        st.error(f"Erro ao excluir: {e}")


def mostrar():
    injetar_css()
    st.title("🚫 Bloqueios de Horários")

    sb = get_supabase()
    empresa_id = st.session_state.empresa_id

    with st.expander("➕ Adicionar Bloqueio", expanded=not st.session_state.get("bloqueios_carregados")):
        tipo = st.radio(
            "Tipo de bloqueio",
            ["Dia inteiro", "Horário específico", "Recorrente semanal"],
            horizontal=True,
            key="tipo_bloqueio"
        )

        motivo = st.text_input("Motivo (opcional)", placeholder="Ex: Férias, Feriado, Almoço...")

        if tipo == "Dia inteiro":
            with st.form("form_bloq_dia"):
                data_bloq = st.date_input("Data", value=date.today(), min_value=date.today(), format="DD/MM/YYYY")
                salvar = st.form_submit_button("🚫 Bloquear dia inteiro", type="primary")
            if salvar:
                _criar_bloqueio(sb, empresa_id, {
                    "tipo": "dia_inteiro",
                    "data": str(data_bloq),
                    "motivo": motivo.strip() or None,
                })

        elif tipo == "Horário específico":
            with st.form("form_bloq_hora"):
                col1, col2, col3 = st.columns(3)
                with col1:
                    data_bloq = st.date_input("Data", value=date.today(), min_value=date.today(), format="DD/MM/YYYY")
                with col2:
                    h_ini = st.time_input("Início", value=datetime.strptime("12:00", "%H:%M").time())
                with col3:
                    h_fim = st.time_input("Fim", value=datetime.strptime("13:00", "%H:%M").time())
                salvar = st.form_submit_button("🚫 Bloquear horário", type="primary")
            if salvar:
                if h_ini >= h_fim:
                    st.error("O horário de início deve ser anterior ao fim.")
                else:
                    _criar_bloqueio(sb, empresa_id, {
                        "tipo": "horario_especifico",
                        "data": str(data_bloq),
                        "hora_inicio": str(h_ini),
                        "hora_fim": str(h_fim),
                        "motivo": motivo.strip() or None,
                    })

        else:  # Recorrente semanal
            with st.form("form_bloq_recorr"):
                col1, col2, col3 = st.columns(3)
                with col1:
                    dia_op = st.selectbox("Dia da semana", list(DIAS_SEMANA.values()), index=1)
                    dia_num = list(DIAS_SEMANA.values()).index(dia_op)
                with col2:
                    h_ini = st.time_input("Início", value=datetime.strptime("12:00", "%H:%M").time(), key="h_ini_rec")
                with col3:
                    h_fim = st.time_input("Fim", value=datetime.strptime("13:00", "%H:%M").time(), key="h_fim_rec")
                salvar = st.form_submit_button("🚫 Criar bloqueio recorrente", type="primary")
            if salvar:
                if h_ini >= h_fim:
                    st.error("O horário de início deve ser anterior ao fim.")
                else:
                    _criar_bloqueio(sb, empresa_id, {
                        "tipo": "recorrente_semanal",
                        "dia_semana": dia_num,
                        "hora_inicio_recorrente": str(h_ini),
                        "hora_fim_recorrente": str(h_fim),
                        "motivo": motivo.strip() or None,
                    })

    # Feriados 2026
    st.divider()
    with st.expander("🇧🇷 Feriados Nacionais 2026"):
        FERIADOS_2026 = [
            ("2026-01-01", "Confraternização Universal"),
            ("2026-02-20", "Carnaval (sexta-feira)"),
            ("2026-02-21", "Carnaval"),
            ("2026-04-03", "Sexta-feira Santa"),
            ("2026-04-21", "Tiradentes"),
            ("2026-05-01", "Dia do Trabalho"),
            ("2026-06-11", "Corpus Christi"),
            ("2026-09-07", "Independência do Brasil"),
            ("2026-10-12", "Nossa Senhora Aparecida"),
            ("2026-11-02", "Finados"),
            ("2026-11-15", "Proclamação da República"),
            ("2026-11-20", "Consciência Negra"),
            ("2026-12-25", "Natal"),
        ]
        st.caption("Clique para importar todos os feriados nacionais de 2026 como bloqueios de dia inteiro.")
        for data_str, nome in FERIADOS_2026:
            d = date.fromisoformat(data_str)
            st.markdown(f"- **{d.strftime('%d/%m/%Y')}** — {nome}")
        st.markdown("")
        if st.button("+ Importar Feriados 2026", type="primary", use_container_width=True):
            importados = ignorados = erros = 0
            for data_str, nome in FERIADOS_2026:
                try:
                    existe = (
                        sb.table("agd_bloqueios").select("id")
                        .eq("empresa_id", empresa_id).eq("tipo", "dia_inteiro")
                        .eq("data", data_str).execute()
                    )
                    if existe.data:
                        ignorados += 1
                        continue
                    sb.table("agd_bloqueios").insert({
                        "empresa_id": empresa_id,
                        "tipo": "dia_inteiro",
                        "data": data_str,
                        "motivo": nome,
                    }).execute()
                    importados += 1
                except Exception:
                    erros += 1
            if importados:
                st.success(f"✅ {importados} feriado(s) importado(s)!")
            if ignorados:
                st.info(f"ℹ️ {ignorados} feriado(s) já cadastrado(s), ignorado(s).")
            if erros:
                st.warning(f"⚠️ {erros} feriado(s) com erro.")
            if importados:
                st.rerun()

    # Lista de bloqueios
    st.subheader("📋 Bloqueios cadastrados")
    try:
        resp = (
            sb.table("agd_bloqueios").select("*")
            .eq("empresa_id", empresa_id)
            .order("criado_em", desc=True)
            .execute()
        )
        bloqueios = resp.data or []
        st.session_state["bloqueios_carregados"] = True
    except Exception as e:
        st.error(f"Erro ao carregar bloqueios: {e}")
        return

    if not bloqueios:
        st.info("Nenhum bloqueio cadastrado.")
        return

    for b in bloqueios:
        tipo = b["tipo"]
        motivo_txt = f" — {b['motivo']}" if b.get("motivo") else ""

        if tipo == "dia_inteiro":
            # Exibir data no formato DD/MM/YYYY
            d = date.fromisoformat(b.get("data", ""))
            desc = f"📅 **Dia inteiro** — {d.strftime('%d/%m/%Y')}{motivo_txt}"
        elif tipo == "horario_especifico":
            d = date.fromisoformat(b.get("data", ""))
            desc = f"⏰ **Horário específico** — {d.strftime('%d/%m/%Y')} das {b.get('hora_inicio','')[:5]} às {b.get('hora_fim','')[:5]}{motivo_txt}"
        else:
            dia_nome = DIAS_SEMANA.get(b.get("dia_semana", 0), "—")
            desc = f"🔁 **Recorrente** — {dia_nome} das {(b.get('hora_inicio_recorrente') or '')[:5]} às {(b.get('hora_fim_recorrente') or '')[:5]}{motivo_txt}"

        col1, col2 = st.columns([5, 1])
        with col1:
            st.markdown(desc)
        with col2:
            if st.button("🗑️", key=f"del_bloq_{b['id'][:8]}", help="Excluir"):
                _excluir_bloqueio(sb, b["id"], empresa_id)
