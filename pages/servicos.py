"""
Serviços — cadastro e gestão dos serviços oferecidos pelo salão.
"""

import streamlit as st
from datetime import datetime, timedelta, timezone
from components.styles import injetar_css
from components.cards import card_servico
from config.supabase_client import get_supabase, get_db_conn

BR_TZ = timezone(timedelta(hours=-3))
OPCOES_DURACAO = [15, 30, 45, 60, 90, 120, 150, 180]


def _salvar_servico(sb, empresa_id: str, dados: dict, servico_id: str = None):
    try:
        if servico_id:
            sb.table("agd_servicos").update(dados).eq("id", servico_id).eq("empresa_id", empresa_id).execute()
            st.success("✅ Serviço atualizado com sucesso!")
        else:
            sb.table("agd_servicos").insert({**dados, "empresa_id": empresa_id}).execute()
            st.success("✅ Serviço cadastrado com sucesso!")
        return True
    except Exception as e:
        st.error(f"Erro ao salvar serviço: {e}")
        return False


def _pode_excluir(conn, servico_id: str, empresa_id: str) -> bool:
    """Verifica se o serviço não tem agendamentos futuros antes de excluir."""
    agora = datetime.now(BR_TZ).isoformat()
    cur = conn.cursor()
    cur.execute("""
        SELECT COUNT(*) FROM agd_agendamentos
        WHERE servico_id = %s AND empresa_id = %s
          AND data_hora_inicio >= %s
          AND status != 'cancelado'
    """, (servico_id, empresa_id, agora))
    count = cur.fetchone()["count"]
    cur.close()
    return count == 0


def _formulario_servico(sb, empresa_id: str, servico: dict = None):
    eh_edicao = servico is not None
    titulo = "✏️ Editar Serviço" if eh_edicao else "➕ Novo Serviço"
    chave = servico["id"][:8] if eh_edicao else "novo"

    with st.form(f"form_servico_{chave}"):
        st.subheader(titulo)

        nome = st.text_input("Nome do serviço *", value=servico["nome"] if eh_edicao else "", placeholder="Ex: Corte feminino")

        duracao_idx = OPCOES_DURACAO.index(servico["duracao_minutos"]) if eh_edicao and servico["duracao_minutos"] in OPCOES_DURACAO else 1
        duracao = st.selectbox("Duração (minutos) *", OPCOES_DURACAO, index=duracao_idx)

        preco = st.number_input("Preço (R$) — opcional", min_value=0.0, step=0.50, format="%.2f",
                                value=float(servico["preco"]) if eh_edicao and servico.get("preco") else 0.0)

        retorno = st.number_input("Retorno sugerido (dias) — opcional", min_value=0, step=1,
                                  value=int(servico["retorno_dias"]) if eh_edicao and servico.get("retorno_dias") else 0,
                                  help="Ex: 35 para coloração. 0 = sem retorno sugerido.")

        ativo = st.checkbox("Serviço ativo", value=servico.get("ativo", True) if eh_edicao else True)

        salvar = st.form_submit_button("💾 Salvar", type="primary", use_container_width=True)

    if salvar:
        if not nome.strip():
            st.error("O nome do serviço é obrigatório.")
            return
        dados = {
            "nome": nome.strip().title(),
            "duracao_minutos": duracao,
            "preco": preco if preco > 0 else None,
            "retorno_dias": retorno if retorno > 0 else None,
            "ativo": ativo,
        }
        ok = _salvar_servico(sb, empresa_id, dados, servico["id"] if eh_edicao else None)
        if ok:
            st.session_state.pop("editando_servico", None)
            st.session_state.pop("mostrar_form_novo", None)
            st.rerun()


def mostrar():
    injetar_css()
    st.title("✂️ Serviços")

    sb = get_supabase()
    conn = get_db_conn()
    empresa_id = st.session_state.empresa_id

    col1, col2 = st.columns([4, 1])
    with col2:
        if st.button("➕ Novo Serviço", type="primary", use_container_width=True):
            st.session_state["mostrar_form_novo"] = True
            st.session_state.pop("editando_servico", None)

    if st.session_state.get("mostrar_form_novo"):
        _formulario_servico(sb, empresa_id)
        if st.button("✕ Cancelar", key="canc_novo"):
            st.session_state.pop("mostrar_form_novo", None)
            st.rerun()
        st.divider()

    try:
        resp = sb.table("agd_servicos").select("*").eq("empresa_id", empresa_id).order("nome").execute()
        servicos = resp.data or []
    except Exception as e:
        st.error(f"Erro ao carregar serviços: {e}")
        return

    if not servicos:
        st.info("Nenhum serviço cadastrado. Clique em **Novo Serviço** para começar.")
        return

    st.caption(f"{len(servicos)} serviço(s) cadastrado(s)")

    for s in servicos:
        if st.session_state.get("editando_servico") == s["id"]:
            _formulario_servico(sb, empresa_id, servico=s)
            if st.button("✕ Cancelar edição", key=f"canc_ed_{s['id'][:8]}"):
                st.session_state.pop("editando_servico", None)
                st.rerun()
            continue

        card_servico(s["nome"], s["duracao_minutos"], s.get("preco"), s.get("retorno_dias"), s.get("ativo", True))

        col_e, col_x, _ = st.columns([1, 1, 4])
        with col_e:
            if st.button("✏️ Editar", key=f"ed_{s['id'][:8]}"):
                st.session_state["editando_servico"] = s["id"]
                st.session_state.pop("mostrar_form_novo", None)
                st.rerun()
        with col_x:
            if st.button("🗑️ Excluir", key=f"del_{s['id'][:8]}"):
                if _pode_excluir(conn, s["id"], empresa_id):
                    try:
                        sb.table("agd_servicos").delete().eq("id", s["id"]).eq("empresa_id", empresa_id).execute()
                        st.success(f"Serviço '{s['nome']}' excluído.")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Erro ao excluir: {e}")
                else:
                    st.warning("⚠️ Este serviço tem agendamentos futuros e não pode ser excluído. Desative-o em vez disso.")
