"""
Componentes de cards reutilizáveis para o AgendaPro.
Funções que geram HTML para cards e badges usados em várias páginas.
"""

import streamlit as st


def card_metrica(titulo: str, valor: str, icone: str, cor: str = "#8B5CF6"):
    """
    Renderiza um card de KPI (métrica) com ícone e valor em destaque.

    Parâmetros:
        titulo: Texto descritivo abaixo do valor
        valor:  Valor principal exibido (ex: "42" ou "R$ 1.200")
        icone:  Emoji ou ícone (ex: "📅")
        cor:    Cor hexadecimal do valor (padrão: roxo)
    """
    st.markdown(f"""
    <div class="card-kpi">
        <div class="kpi-icon">{icone}</div>
        <div class="kpi-valor" style="color:{cor}">{valor}</div>
        <div class="kpi-titulo">{titulo}</div>
    </div>
    """, unsafe_allow_html=True)


def card_agendamento(agendamento: dict, horario: str, nome_cliente: str,
                     nome_servico: str, duracao: int, status: str):
    """
    Renderiza o cabeçalho visual de um card de agendamento.
    Os botões de ação devem ser adicionados pelo chamador usando st.button().

    Parâmetros:
        agendamento:  Dicionário com os dados do agendamento
        horario:      Horário formatado (ex: "09:30")
        nome_cliente: Nome do cliente
        nome_servico: Nome do serviço
        duracao:      Duração em minutos
        status:       Status do agendamento
    """
    cor_borda = {
        "pendente": "#F59E0B",
        "confirmado": "#3B82F6",
        "concluido": "#10B981",
        "cancelado": "#EF4444",
    }.get(status, "#8B5CF6")

    badge = badge_status(status)

    st.markdown(f"""
    <div class="card-agendamento" style="border-left-color:{cor_borda}">
        <div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:8px">
            <div>
                <span style="font-size:1.3rem;font-weight:700">{horario}</span>
                <span style="margin-left:12px;font-size:1rem;font-weight:600">{nome_cliente}</span>
            </div>
            {badge}
        </div>
        <div style="color:#9CA3AF;font-size:0.9rem;margin-top:4px">
            {nome_servico} &bull; {duracao} min
        </div>
    </div>
    """, unsafe_allow_html=True)


def card_servico(nome: str, duracao: int, preco=None, retorno_dias=None, ativo: bool = True):
    """
    Renderiza o visual de um card de serviço.
    Os botões editar/excluir devem ser adicionados pelo chamador.

    Parâmetros:
        nome:         Nome do serviço
        duracao:      Duração em minutos
        preco:        Preço (None se não definido)
        retorno_dias: Dias sugeridos para retorno (None se não aplicável)
        ativo:        Se o serviço está ativo
    """
    preco_txt = f"R$ {preco:.2f}".replace(".", ",") if preco else "Preço não definido"
    retorno_txt = f"🔄 Retorno em {retorno_dias} dias" if retorno_dias else ""
    status_txt = "" if ativo else '<span style="color:#EF4444;font-size:12px">● Inativo</span>'

    st.markdown(f"""
    <div class="card-servico">
        <div style="display:flex;justify-content:space-between;align-items:flex-start">
            <div>
                <div style="font-size:1rem;font-weight:600">{nome} {status_txt}</div>
                <div style="color:#9CA3AF;font-size:0.875rem;margin-top:4px">
                    ⏱ {duracao} min &nbsp;&bull;&nbsp; 💰 {preco_txt}
                    {"&nbsp;&bull;&nbsp;" + retorno_txt if retorno_txt else ""}
                </div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)


def badge_status(status: str) -> str:
    """
    Retorna HTML de um badge colorido para o status do agendamento.
    Use com unsafe_allow_html=True no st.markdown().

    Parâmetros:
        status: "pendente", "confirmado", "concluido" ou "cancelado"
    """
    labels = {
        "pendente": "⏳ Pendente",
        "confirmado": "✅ Confirmado",
        "concluido": "✔️ Concluído",
        "cancelado": "❌ Cancelado",
    }
    label = labels.get(status, status.capitalize())
    return f'<span class="badge badge-{status}">{label}</span>'
