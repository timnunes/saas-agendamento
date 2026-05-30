"""
Lembretes — agendamentos de amanhã para enviar via WhatsApp.
"""

import streamlit as st
from datetime import datetime, timedelta, timezone
from urllib.parse import quote
from components.styles import injetar_css
from config.supabase_client import get_supabase, get_db_conn

BR_TZ = timezone(timedelta(hours=-3))

DIAS_PT = ["Segunda-feira", "Terça-feira", "Quarta-feira", "Quinta-feira", "Sexta-feira", "Sábado", "Domingo"]
MESES_PT = ["janeiro", "fevereiro", "março", "abril", "maio", "junho", "julho",
            "agosto", "setembro", "outubro", "novembro", "dezembro"]


def _data_pt(d) -> str:
    return f"{DIAS_PT[d.weekday()]}, {d.day:02d} de {MESES_PT[d.month-1]} de {d.year}"


def _montar_mensagem(nome_cliente, nome_servico, horario, nome_salao, mensagem_template=None):
    if mensagem_template:
        msg = mensagem_template
    else:
        msg = (
            f"Olá {nome_cliente}! 😊\n"
            f"Lembrando que você tem {nome_servico} agendado amanhã às {horario} no {nome_salao}.\n"
            f"Qualquer dúvida, estamos aqui! ✂️"
        )
    msg = msg.replace("[NOME]", nome_cliente)
    msg = msg.replace("[SERVIÇO]", nome_servico)
    msg = msg.replace("[HORÁRIO]", horario)
    msg = msg.replace("[NOME DO SALÃO]", nome_salao)
    return msg


def mostrar():
    injetar_css()
    st.title("🔔 Lembretes")
    st.caption("Agendamentos de amanhã para enviar lembrete via WhatsApp")

    sb = get_supabase()
    conn = get_db_conn()
    empresa_id = st.session_state.empresa_id
    nome_salao = st.session_state.get("empresa_nome", "nosso salão")

    try:
        conf_resp = (
            sb.table("agd_configuracoes")
            .select("mensagem_confirmacao")
            .eq("empresa_id", empresa_id)
            .execute()
        )
        mensagem_template = None
        if conf_resp.data:
            mensagem_template = conf_resp.data[0].get("mensagem_confirmacao")
    except Exception:
        mensagem_template = None

    amanha = (datetime.now(BR_TZ) + timedelta(days=1)).date()
    amanha_ini = datetime(amanha.year, amanha.month, amanha.day, 0, 0, 0, tzinfo=BR_TZ).isoformat()
    amanha_fim = datetime(amanha.year, amanha.month, amanha.day, 23, 59, 59, tzinfo=BR_TZ).isoformat()

    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT a.id, a.data_hora_inicio, a.lembrete_enviado,
                   c.nome AS cliente_nome, c.telefone AS cliente_telefone,
                   s.nome AS servico_nome
            FROM agd_agendamentos a
            JOIN agd_clientes c ON c.id = a.cliente_id
            JOIN agd_servicos s ON s.id = a.servico_id
            WHERE a.empresa_id = %s
              AND a.status IN ('pendente', 'confirmado')
              AND a.data_hora_inicio >= %s
              AND a.data_hora_inicio <= %s
            ORDER BY a.data_hora_inicio ASC
        """, (empresa_id, amanha_ini, amanha_fim))
        agendamentos = [dict(r) for r in cur.fetchall()]
        cur.close()
    except Exception as e:
        st.error(f"Erro ao carregar agendamentos: {e}")
        return

    st.markdown(f"**{_data_pt(amanha)}** — {len(agendamentos)} agendamento(s)")

    if not agendamentos:
        st.success("✅ Nenhum agendamento pendente para amanhã.")
        return

    for a in agendamentos:
        dt = a["data_hora_inicio"] if isinstance(a["data_hora_inicio"], datetime) else datetime.fromisoformat(str(a["data_hora_inicio"]))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        horario = dt.astimezone(BR_TZ).strftime("%H:%M")

        nome_cliente = a.get("cliente_nome", "—")
        telefone_raw = a.get("cliente_telefone", "") or ""
        nome_servico = a.get("servico_nome", "—")
        lembrete_enviado = a.get("lembrete_enviado", False)

        telefone = "".join(filter(str.isdigit, telefone_raw))
        mensagem = _montar_mensagem(nome_cliente, nome_servico, horario, nome_salao, mensagem_template)
        link_wa = f"https://wa.me/55{telefone}?text={quote(mensagem)}"

        cor_borda = "#10B981" if lembrete_enviado else "#F59E0B"
        st.markdown(f"""
        <div class="card-agendamento" style="border-left-color:{cor_borda}">
            <div style="font-size:1rem;font-weight:600">{horario} — {nome_cliente}</div>
            <div style="color:#9CA3AF;font-size:0.875rem">{nome_servico} &bull; 📱 {telefone_raw}</div>
            {"<div style='color:#10B981;font-size:12px;margin-top:4px'>✅ Lembrete enviado</div>" if lembrete_enviado else ""}
        </div>
        """, unsafe_allow_html=True)

        with st.expander("👁️ Ver mensagem"):
            st.text(mensagem)
            st.code(mensagem, language=None)

        col1, col2, col3, _ = st.columns([1, 1, 1, 2])
        with col1:
            if telefone:
                st.markdown(f'<a href="{link_wa}" target="_blank"><button style="background:#25D366;color:white;border:none;padding:8px 16px;border-radius:8px;cursor:pointer;font-size:14px">📱 WhatsApp</button></a>', unsafe_allow_html=True)
            else:
                st.warning("Sem telefone")
        with col2:
            novo_status = not lembrete_enviado
            label = "☑️ Enviado" if not lembrete_enviado else "↩️ Desmarcar"
            if st.button(label, key=f"lem_{a['id'][:8]}"):
                try:
                    sb.table("agd_agendamentos").update({"lembrete_enviado": novo_status}).eq("id", a["id"]).execute()
                    st.rerun()
                except Exception as e:
                    st.error(f"Erro: {e}")

        st.markdown("---")
