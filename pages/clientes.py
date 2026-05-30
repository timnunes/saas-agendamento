"""
Clientes — lista, busca, cadastro e histórico de atendimentos.
"""

import streamlit as st
from datetime import datetime, timedelta, timezone
from components.styles import injetar_css
from config.supabase_client import get_supabase, get_db_conn

BR_TZ = timezone(timedelta(hours=-3))


def _fmt_dt(iso_str: str) -> str:
    dt = datetime.fromisoformat(iso_str)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(BR_TZ).strftime("%d/%m/%Y %H:%M")


def _historico_cliente(conn, cliente: dict, empresa_id: str):
    with st.expander(f"📋 Histórico de {cliente['nome']}", expanded=True):
        try:
            cur = conn.cursor()
            cur.execute("""
                SELECT a.data_hora_inicio, a.status, s.nome AS servico_nome, s.duracao_minutos
                FROM agd_agendamentos a
                JOIN agd_servicos s ON s.id = a.servico_id
                WHERE a.cliente_id = %s AND a.empresa_id = %s
                ORDER BY a.data_hora_inicio DESC
            """, (cliente["id"], empresa_id))
            agendamentos = [dict(r) for r in cur.fetchall()]
            cur.close()
        except Exception as e:
            st.error(f"Erro ao carregar histórico: {e}")
            return

        if not agendamentos:
            st.info("Nenhum agendamento registrado para este cliente.")
            return

        for a in agendamentos:
            dt_fmt = _fmt_dt(str(a["data_hora_inicio"]))
            nome_serv = a.get("servico_nome", "—")
            status = a.get("status", "—")
            badges = {"pendente": "⏳", "confirmado": "✅", "concluido": "✔️", "cancelado": "❌"}
            icone = badges.get(status, "•")
            st.markdown(
                f"{icone} **{dt_fmt}** — {nome_serv} "
                f"<span style='color:#9CA3AF;font-size:12px'>({status})</span>",
                unsafe_allow_html=True,
            )


def _formulario_editar(sb, cliente: dict, empresa_id: str):
    with st.form(f"edit_cliente_{cliente['id'][:8]}"):
        st.subheader(f"✏️ Editar {cliente['nome']}")
        nome = st.text_input("Nome *", value=cliente["nome"])
        telefone = st.text_input("Telefone *", value=cliente["telefone"])
        email = st.text_input("Email", value=cliente.get("email") or "")
        obs = st.text_area("Observações", value=cliente.get("observacoes") or "")
        salvar = st.form_submit_button("💾 Salvar", type="primary")

    if salvar:
        tel_limpo = "".join(filter(str.isdigit, telefone))
        if not nome.strip() or not tel_limpo:
            st.error("Nome e telefone são obrigatórios.")
            return
        try:
            sb.table("agd_clientes").update({
                "nome": nome.strip().title(),
                "telefone": tel_limpo,
                "email": email.strip() or None,
                "observacoes": obs.strip() or None,
            }).eq("id", cliente["id"]).eq("empresa_id", empresa_id).execute()
            st.success("Cliente atualizado!")
            st.session_state.pop("editando_cliente", None)
            st.rerun()
        except Exception as e:
            st.error(f"Erro ao salvar: {e}")


def _formulario_novo_cliente(sb, empresa_id: str):
    if "counter_novo_cliente" not in st.session_state:
        st.session_state.counter_novo_cliente = 0
    contador = st.session_state.counter_novo_cliente

    with st.expander("➕ Cadastrar novo cliente", expanded=False):
        with st.form(f"form_novo_cliente_{contador}"):
            col1, col2 = st.columns(2)
            with col1:
                nome = st.text_input("Nome *", placeholder="Ex: Maria Silva")
            with col2:
                telefone = st.text_input("Telefone *", placeholder="Ex: 17999990000")
            email = st.text_input("Email", placeholder="Ex: maria@email.com")
            obs = st.text_area("Observações", placeholder="Ex: prefere horário matutino")
            salvar = st.form_submit_button("💾 Cadastrar cliente", type="primary")

        if salvar:
            tel_limpo = "".join(filter(str.isdigit, telefone))
            if not nome.strip() or not tel_limpo:
                st.error("Nome e telefone são obrigatórios.")
                return
            try:
                sb.table("agd_clientes").insert({
                    "empresa_id": empresa_id,
                    "nome": nome.strip().title(),
                    "telefone": tel_limpo,
                    "email": email.strip() or None,
                    "observacoes": obs.strip() or None,
                }).execute()
                st.success(f"✅ Cliente {nome.strip().title()} cadastrado com sucesso!")
                st.session_state.counter_novo_cliente += 1
                st.rerun()
            except Exception as e:
                erro = str(e)
                if "unique" in erro.lower():
                    st.error("❌ Já existe um cliente com este telefone.")
                else:
                    st.error(f"Erro ao cadastrar: {e}")


def mostrar():
    injetar_css()
    st.title("👥 Clientes")

    sb = get_supabase()
    conn = get_db_conn()
    empresa_id = st.session_state.empresa_id

    _formulario_novo_cliente(sb, empresa_id)
    st.divider()

    busca = st.text_input("🔍 Buscar por nome ou telefone", placeholder="Ex: Maria ou 11999990000")

    try:
        q = sb.table("agd_clientes").select("*").eq("empresa_id", empresa_id).order("nome")
        if busca.strip():
            q = q.or_(f"nome.ilike.%{busca}%,telefone.ilike.%{busca}%")
        resp = q.execute()
        clientes = resp.data or []
    except Exception as e:
        st.error(f"Erro ao buscar clientes: {e}")
        return

    st.caption(f"{len(clientes)} cliente(s) encontrado(s)")

    if not clientes:
        if busca:
            st.info("Nenhum cliente encontrado com essa busca.")
        else:
            st.info("Nenhum cliente cadastrado ainda.")
        return

    for c in clientes:
        try:
            cur = conn.cursor()
            cur.execute("""
                SELECT data_hora_inicio FROM agd_agendamentos
                WHERE cliente_id = %s AND empresa_id = %s AND status = 'concluido'
                ORDER BY data_hora_inicio DESC
            """, (c["id"], empresa_id))
            hist = cur.fetchall()
            cur.close()
            total_visitas = len(hist)
            ultimo = _fmt_dt(str(hist[0]["data_hora_inicio"])) if hist else "—"
        except Exception:
            total_visitas = 0
            ultimo = "—"

        col1, col2, col3, col4 = st.columns([3, 2, 1, 1])
        with col1:
            st.markdown(f"**{c['nome']}**  \n📱 {c['telefone']}")
        with col2:
            st.markdown(f"Último: {ultimo}")
        with col3:
            st.markdown(f"🗓 {total_visitas} visita(s)")
        with col4:
            if st.button("✏️", key=f"edit_c_{c['id'][:8]}", help="Editar"):
                if st.session_state.get("editando_cliente") == c["id"]:
                    st.session_state.pop("editando_cliente", None)
                else:
                    st.session_state["editando_cliente"] = c["id"]
                    st.session_state.pop("historico_cliente", None)
                st.rerun()

        if st.button(f"Ver histórico de {c['nome']}", key=f"hist_c_{c['id'][:8]}"):
            if st.session_state.get("historico_cliente") == c["id"]:
                st.session_state.pop("historico_cliente", None)
            else:
                st.session_state["historico_cliente"] = c["id"]
                st.session_state.pop("editando_cliente", None)
            st.rerun()

        if st.session_state.get("historico_cliente") == c["id"]:
            _historico_cliente(conn, c, empresa_id)

        if st.session_state.get("editando_cliente") == c["id"]:
            _formulario_editar(sb, c, empresa_id)
            if st.button("✕ Cancelar edição", key=f"canc_ec_{c['id'][:8]}"):
                st.session_state.pop("editando_cliente", None)
                st.rerun()

        st.divider()
