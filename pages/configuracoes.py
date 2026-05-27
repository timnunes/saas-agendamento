"""
Configurações do salão.

Abas:
  - Horários de funcionamento (dias, abertura, fechamento, almoço, granularidade)
  - Dados do salão (nome, telefone, endereço, link público)
  - Mensagens (textos padrão de confirmação e lembrete)
"""

import streamlit as st
from datetime import datetime, timedelta, timezone, time
from components.styles import injetar_css
from config.supabase_client import get_supabase

BR_TZ = timezone(timedelta(hours=-3))

DIAS = {0: "Dom", 1: "Seg", 2: "Ter", 3: "Qua", 4: "Qui", 5: "Sex", 6: "Sáb"}


def _parse_time(t_str: str | None) -> time | None:
    """Converte string 'HH:MM:SS' ou 'HH:MM' para objeto time."""
    if not t_str:
        return None
    partes = t_str.split(":")
    return time(int(partes[0]), int(partes[1]))


def _carregar_config(sb, empresa_id: str) -> dict | None:
    resp = sb.table("agd_configuracoes").select("*").eq("empresa_id", empresa_id).execute()
    return resp.data[0] if resp.data else None


def _salvar_config(sb, empresa_id: str, dados: dict, config_id: str = None):
    try:
        if config_id:
            sb.table("agd_configuracoes").update(dados).eq("id", config_id).execute()
        else:
            sb.table("agd_configuracoes").insert({**dados, "empresa_id": empresa_id}).execute()
        st.success("✅ Configurações salvas!")
        st.rerun()
    except Exception as e:
        st.error(f"Erro ao salvar: {e}")


def _aba_horarios(sb, empresa_id: str, config: dict | None):
    """Aba de horários de funcionamento."""
    config_id = config["id"] if config else None

    # Valores atuais ou padrões
    dias_func = config.get("dias_funcionamento", [1, 2, 3, 4, 5, 6]) if config else [1, 2, 3, 4, 5, 6]
    h_aber = _parse_time(config.get("hora_abertura")) or time(8, 0) if config else time(8, 0)
    h_fech = _parse_time(config.get("hora_fechamento")) or time(18, 0) if config else time(18, 0)
    alm_ini = _parse_time(config.get("tempo_almoco_inicio")) if config else None
    alm_fim = _parse_time(config.get("tempo_almoco_fim")) if config else None
    intervalo = config.get("intervalo_minutos", 30) if config else 30

    with st.form("form_horarios"):
        st.subheader("📆 Dias de funcionamento")
        dias_sel = []
        cols = st.columns(7)
        for num, nome in DIAS.items():
            with cols[num]:
                if st.checkbox(nome, value=(num in dias_func), key=f"dia_{num}"):
                    dias_sel.append(num)

        st.divider()
        st.subheader("🕐 Horários")

        col1, col2, col3 = st.columns(3)
        with col1:
            abertura = st.time_input("Abertura", value=h_aber)
        with col2:
            fechamento = st.time_input("Fechamento", value=h_fech)
        with col3:
            granularidade = st.selectbox("Granularidade dos slots", [30, 60],
                                         index=0 if intervalo == 30 else 1,
                                         format_func=lambda x: f"{x} minutos")

        st.divider()
        st.subheader("🍽️ Intervalo de almoço (opcional)")
        tem_almoco = st.checkbox("Definir intervalo de almoço", value=bool(alm_ini))

        al_ini = al_fim = None
        if tem_almoco:
            col4, col5 = st.columns(2)
            with col4:
                al_ini = st.time_input("Início do almoço", value=alm_ini or time(12, 0))
            with col5:
                al_fim = st.time_input("Fim do almoço", value=alm_fim or time(13, 0))

        salvar = st.form_submit_button("💾 Salvar horários", type="primary")

    if salvar:
        if abertura >= fechamento:
            st.error("O horário de abertura deve ser anterior ao fechamento.")
            return
        if not dias_sel:
            st.error("Selecione pelo menos um dia de funcionamento.")
            return

        dados = {
            "dias_funcionamento": dias_sel,
            "hora_abertura": str(abertura),
            "hora_fechamento": str(fechamento),
            "intervalo_minutos": granularidade,
            "tempo_almoco_inicio": str(al_ini) if al_ini else None,
            "tempo_almoco_fim": str(al_fim) if al_fim else None,
        }
        _salvar_config(sb, empresa_id, dados, config_id)


def _aba_dados(sb, empresa_id: str):
    """Aba de dados do salão."""
    try:
        resp = sb.table("agd_empresas").select("*").eq("id", empresa_id).execute()
        empresa = resp.data[0] if resp.data else {}
    except Exception as e:
        st.error(f"Erro ao carregar dados: {e}")
        return

    slug = empresa.get("slug", "")
    link_publico = f"https://agendapro.streamlit.app/?slug={slug}"

    with st.form("form_dados_salao"):
        nome = st.text_input("Nome do salão *", value=empresa.get("nome", ""))
        telefone = st.text_input("Telefone de contato", value=empresa.get("telefone") or "")
        endereco = st.text_area("Endereço", value=empresa.get("endereco") or "")
        st.text_input("🔗 Link público (somente leitura)", value=link_publico, disabled=True)
        salvar = st.form_submit_button("💾 Salvar dados", type="primary")

    if salvar:
        if not nome.strip():
            st.error("O nome do salão é obrigatório.")
            return
        tel_limpo = "".join(filter(str.isdigit, telefone)) if telefone else None
        try:
            sb.table("agd_empresas").update({
                "nome": nome.strip().title(),
                "telefone": tel_limpo,
                "endereco": endereco.strip() or None,
            }).eq("id", empresa_id).execute()
            st.session_state["empresa_nome"] = nome.strip().title()
            st.success("✅ Dados do salão atualizados!")
        except Exception as e:
            st.error(f"Erro ao salvar: {e}")


def _aba_mensagens(sb, empresa_id: str, config: dict | None):
    """Aba de mensagens padrão."""
    config_id = config["id"] if config else None
    msg_confirm = config.get("mensagem_confirmacao") if config else None

    msg_default_confirm = (
        "Olá [NOME]! 😊\n"
        "Lembrando que você tem [SERVIÇO] agendado amanhã às [HORÁRIO] no [NOME DO SALÃO].\n"
        "Qualquer dúvida, estamos aqui! ✂️"
    )

    with st.form("form_mensagens"):
        st.subheader("💬 Mensagem de lembrete")
        st.caption("Variáveis disponíveis: [NOME], [SERVIÇO], [HORÁRIO], [NOME DO SALÃO]")
        mensagem = st.text_area(
            "Texto da mensagem",
            value=msg_confirm or msg_default_confirm,
            height=150,
        )
        salvar = st.form_submit_button("💾 Salvar mensagens", type="primary")

    if salvar:
        dados = {"mensagem_confirmacao": mensagem.strip()}
        _salvar_config(sb, empresa_id, dados, config_id)


def mostrar():
    injetar_css()
    st.title("⚙️ Configurações")

    sb = get_supabase()
    empresa_id = st.session_state.empresa_id

    # Carregar configurações uma vez
    try:
        config = _carregar_config(sb, empresa_id)
    except Exception as e:
        st.error(f"Erro ao carregar configurações: {e}")
        return

    aba_hor, aba_dados, aba_msg = st.tabs(["🕐 Horários", "🏪 Dados do Salão", "💬 Mensagens"])

    with aba_hor:
        _aba_horarios(sb, empresa_id, config)

    with aba_dados:
        _aba_dados(sb, empresa_id)

    with aba_msg:
        _aba_mensagens(sb, empresa_id, config)
