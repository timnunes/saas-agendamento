"""
CSS customizado injetado via st.markdown.
Aplica o design visual do AgendaPro em todas as páginas.
Otimizado para uso em celular (touch-friendly, fontes legíveis, botões grandes).
"""
import streamlit as st


def injetar_css():
    """Injeta o CSS customizado na página atual."""
    st.markdown("""
    <style>

    /* ===== DESIGN TOKENS ===== */
    :root {
        --primary:        #8B5CF6;
        --primary-dark:   #6D28D9;
        --success:        #10B981;
        --warning:        #F59E0B;
        --danger:         #EF4444;
        --neutral:        #6B7280;
        --bg-card:        #1F2937;
        --text-primary:   #F9FAFB;
        --text-secondary: #9CA3AF;
    }

    /* ===== CARDS ===== */
    .card {
        background: var(--bg-card);
        border-radius: 12px;
        padding: 1.5rem;
        border: 1px solid rgba(139, 92, 246, 0.2);
        margin-bottom: 1rem;
    }
    .card-kpi {
        background: #1F2937;
        border-radius: 12px;
        padding: 1.25rem 1.5rem;
        border: 1px solid rgba(139, 92, 246, 0.25);
        margin-bottom: 0.75rem;
        text-align: center;
    }
    .card-kpi .kpi-icon   { font-size: 2rem; margin-bottom: 0.25rem; }
    .card-kpi .kpi-valor  { font-size: 2rem; font-weight: 700; color: #8B5CF6; }
    .card-kpi .kpi-titulo { font-size: 0.85rem; color: #9CA3AF; margin-top: 0.2rem; }

    .card-agendamento {
        background: #1F2937;
        border-radius: 10px;
        padding: 1rem 1.25rem;
        border-left: 4px solid #8B5CF6;
        margin-bottom: 0.75rem;
    }
    .card-servico {
        background: #1F2937;
        border-radius: 10px;
        padding: 1rem 1.25rem;
        border: 1px solid rgba(139, 92, 246, 0.2);
        margin-bottom: 0.75rem;
    }

    /* ===== BADGES DE STATUS ===== */
    .badge {
        display: inline-block;
        padding: 3px 12px;
        border-radius: 12px;
        font-size: 12px;
        font-weight: 600;
    }
    .badge-pendente   { background: #F59E0B22; color: #F59E0B; }
    .badge-confirmado { background: #3B82F622; color: #3B82F6; }
    .badge-concluido  { background: #10B98122; color: #10B981; }
    .badge-cancelado  { background: #EF444422; color: #EF4444; }

    /* ===== BOTÕES PRIMÁRIOS ===== */
    .stButton > button[kind="primary"] {
        background: #8B5CF6;
        border-radius: 8px;
        font-weight: 600;
        padding: 0.6rem 1.5rem;
        border: none;
    }
    .stButton > button[kind="primary"]:hover {
        background: #6D28D9;
    }

    /* ===== SLOTS DE HORÁRIO (página pública) ===== */
    .slot-grid {
        display: flex;
        flex-wrap: wrap;
        gap: 8px;
        margin: 1rem 0;
    }

    /* ===== SIDEBAR ===== */
    .empresa-nome-sidebar {
        font-size: 1rem;
        font-weight: 700;
        color: #8B5CF6;
        padding: 0.5rem 0;
    }

    /* ===================================================
       MOBILE — tudo abaixo de 768px
       Foco: toque fácil, leitura confortável, sem zoom
    ===================================================== */
    @media (max-width: 768px) {

        /* Menos padding nas bordas da tela */
        .main .block-container {
            padding: 0.75rem 0.75rem 4rem 0.75rem !important;
            max-width: 100% !important;
        }

        /* Título das páginas menor */
        h1 { font-size: 1.4rem !important; margin-bottom: 0.5rem !important; }
        h2 { font-size: 1.2rem !important; }
        h3 { font-size: 1.05rem !important; }

        /* Texto corrido mais legível */
        p, li, .stMarkdown { font-size: 0.95rem !important; line-height: 1.5 !important; }

        /* KPI menor mas ainda legível */
        .card-kpi .kpi-valor  { font-size: 1.6rem !important; }
        .card-kpi .kpi-titulo { font-size: 0.8rem !important; }
        .card-kpi             { padding: 1rem !important; }

        /* Botões grandes para toque fácil */
        .stButton > button {
            min-height: 48px !important;
            font-size: 1rem !important;
            padding: 0.6rem 1rem !important;
            width: 100% !important;
            border-radius: 10px !important;
        }

        /* Inputs grandes para toque */
        input, textarea, select,
        .stTextInput input,
        .stSelectbox select,
        .stTimeInput input,
        .stDateInput input {
            font-size: 1rem !important;
            min-height: 44px !important;
        }

        /* Abas mais largas e fáceis de tocar */
        .stTabs [data-baseweb="tab"] {
            font-size: 0.9rem !important;
            padding: 0.6rem 0.75rem !important;
            min-height: 44px !important;
        }

        /* Expanders com padding generoso */
        .streamlit-expanderHeader {
            font-size: 0.95rem !important;
            padding: 0.75rem 1rem !important;
            min-height: 48px !important;
        }

        /* Colunas empilham verticalmente em telas pequenas */
        [data-testid="column"] {
            width: 100% !important;
            flex: 1 1 100% !important;
            min-width: 0 !important;
        }

        /* Dividers mais discretos */
        hr { margin: 0.75rem 0 !important; }

        /* Sidebar: fecha por padrão no celular (comportamento nativo do Streamlit) */
        /* O ícone de hambúrguer fica visível automaticamente */

        /* Caption e textos pequenos */
        .stCaption, small { font-size: 0.82rem !important; }

        /* Formulários sem espaço desperdiçado */
        .stForm { padding: 0.75rem !important; }

        /* Slider mais fácil de arrastar */
        .stSlider [data-baseweb="slider"] {
            padding: 0.5rem 0 !important;
        }
        .stSlider [role="slider"] {
            width: 28px !important;
            height: 28px !important;
        }

        /* Número de paginação centralizado */
        .stNumberInput { text-align: center !important; }

        /* Cards com menos padding */
        .card, .card-agendamento, .card-servico {
            padding: 0.85rem 1rem !important;
        }
    }

    </style>
    """, unsafe_allow_html=True)
