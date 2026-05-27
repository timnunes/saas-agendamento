"""
Retenção — clientes com data de retorno sugerida nos próximos 7 dias.

Para cada cliente no prazo de retorno:
  - Mostra nome, último serviço, data sugerida de retorno
  - Gera link wa.me com mensagem de reativação
"""

import streamlit as st
from datetime import datetime, timedelta, timezone
from urllib.parse import quote
from components.styles import injetar_css
from config.supabase_client import get_supabase

BR_TZ = timezone(timedelta(hours=-3))


def _link_publico(slug: str) -> str:
    """Gera o link público do salão para incluir na mensagem."""
    # Em produção, substitua pela URL real do app no Streamlit Cloud
    app_url = "https://agendapro.streamlit.app"
    return f"{app_url}/?slug={slug}"


def mostrar():
    injetar_css()
    st.title("🔄 Retenção de Clientes")
    st.caption("Clientes com retorno sugerido para os próximos 7 dias")

    sb = get_supabase()
    empresa_id = st.session_state.empresa_id
    nome_salao = st.session_state.get("empresa_nome", "nosso salão")
    slug = st.session_state.get("empresa_slug", "")

    hoje = datetime.now(BR_TZ).date()
    prazo = hoje + timedelta(days=7)

    try:
        resp = (
            sb.table("agd_agendamentos")
            .select("*, agd_clientes(nome, telefone), agd_servicos(nome)")
            .eq("empresa_id", empresa_id)
            .eq("status", "concluido")
            .gte("data_retorno_sugerida", str(hoje))
            .lte("data_retorno_sugerida", str(prazo))
            .order("data_retorno_sugerida")
            .execute()
        )
        agendamentos = resp.data or []
    except Exception as e:
        st.error(f"Erro ao carregar dados: {e}")
        return

    st.markdown(f"**{len(agendamentos)}** cliente(s) para reativar esta semana")

    if not agendamentos:
        st.success("✅ Nenhum cliente para reativar agora.")
        return

    link_salao = _link_publico(slug)

    for a in agendamentos:
        nome_cliente = (a.get("agd_clientes") or {}).get("nome", "—")
        telefone_raw = (a.get("agd_clientes") or {}).get("telefone", "")
        nome_servico = (a.get("agd_servicos") or {}).get("nome", "—")
        data_retorno = a.get("data_retorno_sugerida", "—")

        # Formatar data do último atendimento
        dt = datetime.fromisoformat(a["data_hora_inicio"])
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        data_atend = dt.astimezone(BR_TZ).strftime("%d/%m/%Y")

        # Dias faltando para o retorno
        try:
            dias_retorno = (datetime.strptime(data_retorno, "%Y-%m-%d").date() - hoje).days
            dias_txt = f"Retorno em {dias_retorno} dia(s)" if dias_retorno > 0 else "Retorno hoje!"
        except Exception:
            dias_txt = ""

        # Mensagem de reativação
        mensagem = (
            f"Olá {nome_cliente}! 🌟\n"
            f"Faz um tempo que você veio aqui no {nome_salao}!\n"
            f"Que tal agendar seu próximo {nome_servico}?\n"
            f"Acesse nosso link para ver os horários disponíveis:\n{link_salao}"
        )
        telefone = "".join(filter(str.isdigit, telefone_raw))
        link_wa = f"https://wa.me/55{telefone}?text={quote(mensagem)}"

        # Card
        st.markdown(f"""
        <div class="card-agendamento" style="border-left-color:#8B5CF6">
            <div style="font-size:1rem;font-weight:600">{nome_cliente}</div>
            <div style="color:#9CA3AF;font-size:0.875rem">
                Último: {nome_servico} em {data_atend} &bull; 📱 {telefone_raw}
            </div>
            <div style="color:#8B5CF6;font-size:12px;margin-top:4px">🗓 {dias_txt}</div>
        </div>
        """, unsafe_allow_html=True)

        with st.expander("👁️ Ver mensagem de reativação"):
            st.text(mensagem)
            st.code(mensagem, language=None)

        col1, _ = st.columns([1, 3])
        with col1:
            if telefone:
                st.markdown(
                    f'<a href="{link_wa}" target="_blank">'
                    f'<button style="background:#25D366;color:white;border:none;padding:8px 16px;border-radius:8px;cursor:pointer;font-size:14px">'
                    f'📱 Reativar via WhatsApp</button></a>',
                    unsafe_allow_html=True,
                )
            else:
                st.warning("Telefone não cadastrado")

        st.markdown("---")
