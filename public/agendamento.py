"""
Página pública de agendamento online.

Acesso via: https://seuapp.streamlit.app/?slug=nome-do-salao
NÃO requer login. Qualquer pessoa com o link pode agendar.

Fluxo em 5 passos:
  1. Escolher serviço
  2. Escolher data
  3. Escolher horário (slots disponíveis)
  4. Preencher dados pessoais
  5. Confirmação do agendamento
"""

import streamlit as st
from datetime import datetime, timedelta, timezone, date, time
from config.supabase_client import get_supabase

BR_TZ = timezone(timedelta(hours=-3))


# ===== UTILITÁRIOS =====

def _parse_time_str(t_str: str | None) -> time | None:
    """Converte 'HH:MM:SS' em objeto time."""
    if not t_str:
        return None
    partes = t_str.split(":")
    return time(int(partes[0]), int(partes[1]))


def _gerar_slots(config: dict, data: date, duracao_min: int) -> list[datetime]:
    """
    Gera todos os slots de horário válidos para uma data e duração.
    Considera: horário de funcionamento, almoço e granularidade.
    """
    h_aber = _parse_time_str(config.get("hora_abertura")) or time(8, 0)
    h_fech = _parse_time_str(config.get("hora_fechamento")) or time(18, 0)
    intervalo = config.get("intervalo_minutos", 30)
    alm_ini = _parse_time_str(config.get("tempo_almoco_inicio"))
    alm_fim = _parse_time_str(config.get("tempo_almoco_fim"))

    # Converter para datetime com fuso BRT
    inicio_dia = datetime(data.year, data.month, data.day, h_aber.hour, h_aber.minute, tzinfo=BR_TZ)
    fim_dia = datetime(data.year, data.month, data.day, h_fech.hour, h_fech.minute, tzinfo=BR_TZ)

    alm_ini_dt = datetime(data.year, data.month, data.day, alm_ini.hour, alm_ini.minute, tzinfo=BR_TZ) if alm_ini else None
    alm_fim_dt = datetime(data.year, data.month, data.day, alm_fim.hour, alm_fim.minute, tzinfo=BR_TZ) if alm_fim else None

    slots = []
    slot = inicio_dia

    while slot + timedelta(minutes=duracao_min) <= fim_dia:
        slot_fim = slot + timedelta(minutes=duracao_min)

        # Verificar intervalo de almoço
        if alm_ini_dt and alm_fim_dt:
            if not (slot_fim <= alm_ini_dt or slot >= alm_fim_dt):
                slot += timedelta(minutes=intervalo)
                continue

        slots.append(slot)
        slot += timedelta(minutes=intervalo)

    return slots


def _filtrar_slots_disponiveis(sb, empresa_id: str, data: date,
                               duracao_min: int, slots: list[datetime]) -> list[datetime]:
    """
    Remove slots ocupados por agendamentos existentes e bloqueios.
    Retorna apenas os slots livres.
    """
    if not slots:
        return []

    # Buscar agendamentos do dia
    ini_dia = datetime(data.year, data.month, data.day, 0, 0, 0, tzinfo=BR_TZ).isoformat()
    fim_dia = datetime(data.year, data.month, data.day, 23, 59, 59, tzinfo=BR_TZ).isoformat()

    try:
        resp_agend = (
            sb.table("agd_agendamentos")
            .select("data_hora_inicio, data_hora_fim, status")
            .eq("empresa_id", empresa_id)
            .gte("data_hora_inicio", ini_dia)
            .lte("data_hora_inicio", fim_dia)
            .neq("status", "cancelado")
            .execute()
        )
        agendamentos = resp_agend.data or []
    except Exception:
        agendamentos = []

    # Normalizar timestamps dos agendamentos
    agend_norm = []
    for a in agendamentos:
        ag_ini = datetime.fromisoformat(a["data_hora_inicio"])
        ag_fim = datetime.fromisoformat(a["data_hora_fim"])
        if ag_ini.tzinfo is None:
            ag_ini = ag_ini.replace(tzinfo=timezone.utc)
        if ag_fim.tzinfo is None:
            ag_fim = ag_fim.replace(tzinfo=timezone.utc)
        agend_norm.append((ag_ini, ag_fim))

    # Buscar bloqueios
    try:
        resp_bloq = (
            sb.table("agd_bloqueios")
            .select("*")
            .eq("empresa_id", empresa_id)
            .execute()
        )
        bloqueios = resp_bloq.data or []
    except Exception:
        bloqueios = []

    # Schema: 0=Dom, 1=Seg..., 6=Sáb; Python weekday: 0=Mon, 6=Sun
    dia_schema = (data.weekday() + 1) % 7

    livres = []
    for slot in slots:
        slot_fim = slot + timedelta(minutes=duracao_min)
        ocupado = False

        # Verificar agendamentos
        for ag_ini, ag_fim in agend_norm:
            if ag_ini < slot_fim and ag_fim > slot:
                ocupado = True
                break

        if ocupado:
            continue

        # Verificar bloqueios
        for b in bloqueios:
            tipo = b["tipo"]

            if tipo == "dia_inteiro" and b.get("data") == str(data):
                ocupado = True
                break

            elif tipo == "horario_especifico" and b.get("data") == str(data):
                h_ini = _parse_time_str(b.get("hora_inicio"))
                h_fim = _parse_time_str(b.get("hora_fim"))
                if h_ini and h_fim:
                    bl_ini = datetime(data.year, data.month, data.day, h_ini.hour, h_ini.minute, tzinfo=BR_TZ)
                    bl_fim = datetime(data.year, data.month, data.day, h_fim.hour, h_fim.minute, tzinfo=BR_TZ)
                    if bl_ini < slot_fim and bl_fim > slot:
                        ocupado = True
                        break

            elif tipo == "recorrente_semanal" and b.get("dia_semana") == dia_schema:
                h_ini = _parse_time_str(b.get("hora_inicio_recorrente"))
                h_fim = _parse_time_str(b.get("hora_fim_recorrente"))
                if h_ini and h_fim:
                    bl_ini = datetime(data.year, data.month, data.day, h_ini.hour, h_ini.minute, tzinfo=BR_TZ)
                    bl_fim = datetime(data.year, data.month, data.day, h_fim.hour, h_fim.minute, tzinfo=BR_TZ)
                    if bl_ini < slot_fim and bl_fim > slot:
                        ocupado = True
                        break

        if not ocupado:
            livres.append(slot)

    return livres


def _obter_ou_criar_cliente(sb, empresa_id: str, nome: str, telefone: str, email: str | None) -> str | None:
    """
    Busca cliente pelo telefone + empresa_id.
    Se existir, retorna o ID. Se não existir, cria um novo.
    """
    try:
        resp = (
            sb.table("agd_clientes")
            .select("id, nome")
            .eq("empresa_id", empresa_id)
            .eq("telefone", telefone)
            .execute()
        )

        if resp.data:
            # Cliente já existe — retornar ID
            return resp.data[0]["id"]

        # Criar novo cliente
        novo = (
            sb.table("agd_clientes")
            .insert({
                "empresa_id": empresa_id,
                "nome": nome.strip().title(),
                "telefone": telefone,
                "email": email.strip() if email else None,
            })
            .execute()
        )
        return novo.data[0]["id"] if novo.data else None

    except Exception as e:
        st.error(f"Erro ao cadastrar cliente: {e}")
        return None


def _salvar_agendamento(sb, empresa_id: str, cliente_id: str,
                         servico_id: str, inicio: datetime, duracao_min: int) -> bool:
    """Salva o agendamento no banco de dados."""
    fim = inicio + timedelta(minutes=duracao_min)
    try:
        sb.table("agd_agendamentos").insert({
            "empresa_id": empresa_id,
            "cliente_id": cliente_id,
            "servico_id": servico_id,
            "data_hora_inicio": inicio.isoformat(),
            "data_hora_fim": fim.isoformat(),
            "status": "pendente",
        }).execute()
        return True
    except Exception as e:
        st.error(f"Erro ao salvar agendamento: {e}")
        return False


# ===== PONTO DE ENTRADA =====

def mostrar_agendamento(slug: str):
    """Ponto de entrada da página pública de agendamento."""
    sb = get_supabase()

    # Buscar empresa pelo slug
    try:
        resp_emp = sb.table("agd_empresas").select("*").eq("slug", slug).execute()
    except Exception as e:
        st.error(f"Erro ao carregar página: {e}")
        return

    if not resp_emp.data:
        st.error("😕 Página de agendamento não encontrada.")
        st.caption(f"Verifique se o endereço está correto: ...?slug={slug}")
        return

    empresa = resp_emp.data[0]
    empresa_id = empresa["id"]
    cor = empresa.get("cor_primaria", "#8B5CF6")

    # Cabeçalho do salão
    st.markdown(f"""
    <div style="background:{cor}15;border-left:4px solid {cor};padding:1rem 1.5rem;border-radius:0 12px 12px 0;margin-bottom:1.5rem">
        <h2 style="color:{cor};margin:0">✂️ {empresa['nome']}</h2>
        <p style="color:#9CA3AF;margin:4px 0 0">Agendamento online</p>
    </div>
    """, unsafe_allow_html=True)

    # Carregar serviços e configurações
    try:
        resp_serv = (
            sb.table("agd_servicos")
            .select("*")
            .eq("empresa_id", empresa_id)
            .eq("ativo", True)
            .order("nome")
            .execute()
        )
        servicos = resp_serv.data or []

        resp_conf = (
            sb.table("agd_configuracoes")
            .select("*")
            .eq("empresa_id", empresa_id)
            .execute()
        )
        config = resp_conf.data[0] if resp_conf.data else {}
    except Exception as e:
        st.error(f"Erro ao carregar dados do salão: {e}")
        return

    if not servicos:
        st.warning("Nenhum serviço disponível no momento.")
        return

    # Inicializar estado do fluxo de agendamento
    if "pub_step" not in st.session_state:
        st.session_state.pub_step = 1

    step = st.session_state.pub_step

    # ===== PASSO 1: ESCOLHER SERVIÇO =====
    if step == 1:
        st.subheader("1️⃣ Escolha o serviço")

        for s in servicos:
            preco_txt = f"R$ {s['preco']:.2f}".replace(".", ",") if s.get("preco") else "Consultar"
            selecionado = st.session_state.get("pub_servico_id") == s["id"]
            borda = f"2px solid {cor}" if selecionado else "1px solid #374151"

            st.markdown(f"""
            <div style="background:#1F2937;border:{borda};border-radius:10px;padding:1rem;margin-bottom:8px">
                <div style="font-weight:600">{s['nome']}</div>
                <div style="color:#9CA3AF;font-size:0.875rem">⏱ {s['duracao_minutos']} min &bull; 💰 {preco_txt}</div>
            </div>
            """, unsafe_allow_html=True)

            if st.button(f"Selecionar: {s['nome']}", key=f"serv_{s['id'][:8]}", use_container_width=True):
                st.session_state.pub_servico_id = s["id"]
                st.session_state.pub_servico_nome = s["nome"]
                st.session_state.pub_duracao = s["duracao_minutos"]
                st.session_state.pub_step = 2
                st.rerun()

    # ===== PASSO 2: ESCOLHER DATA =====
    elif step == 2:
        st.subheader("2️⃣ Escolha a data")
        st.caption(f"Serviço: **{st.session_state.get('pub_servico_nome')}**")

        dias_func = config.get("dias_funcionamento", [1, 2, 3, 4, 5, 6])

        # Determinar datas bloqueadas (dia inteiro)
        try:
            resp_bloq = (
                sb.table("agd_bloqueios")
                .select("data, tipo, dia_semana")
                .eq("empresa_id", empresa_id)
                .execute()
            )
            bloqueios_data = resp_bloq.data or []
        except Exception:
            bloqueios_data = []

        datas_bloqueadas = {b["data"] for b in bloqueios_data if b["tipo"] == "dia_inteiro" and b.get("data")}

        data_sel = st.date_input(
            "Data do agendamento",
            value=date.today() + timedelta(days=1),
            min_value=date.today(),
            help="Escolha uma data disponível"
        )

        # Verificar se a data é válida
        dia_schema = (data_sel.weekday() + 1) % 7
        bloq_recorr = [b for b in bloqueios_data if b["tipo"] == "recorrente_semanal" and b.get("dia_semana") == dia_schema]
        dia_inteiro_bloq = [b for b in bloqueios_data if b["tipo"] == "dia_inteiro" and b.get("data") == str(data_sel)]

        avisos = []
        if dia_schema not in dias_func:
            avisos.append("⚠️ O salão não funciona neste dia da semana.")
        if dia_inteiro_bloq:
            motivo = dia_inteiro_bloq[0].get("motivo") or "bloqueio"
            avisos.append(f"⚠️ Este dia está bloqueado ({motivo}).")

        for a in avisos:
            st.warning(a)

        col1, col2 = st.columns(2)
        with col1:
            if st.button("← Voltar", use_container_width=True):
                st.session_state.pub_step = 1
                st.rerun()
        with col2:
            if not avisos:
                if st.button("Continuar →", type="primary", use_container_width=True):
                    st.session_state.pub_data = data_sel
                    st.session_state.pub_step = 3
                    st.rerun()

    # ===== PASSO 3: ESCOLHER HORÁRIO =====
    elif step == 3:
        st.subheader("3️⃣ Escolha o horário")
        data = st.session_state.get("pub_data", date.today())
        duracao = st.session_state.get("pub_duracao", 30)

        st.caption(f"Serviço: **{st.session_state.get('pub_servico_nome')}** &bull; Data: **{data.strftime('%d/%m/%Y')}**")

        # Gerar e filtrar slots
        todos_slots = _gerar_slots(config, data, duracao)
        slots_livres = _filtrar_slots_disponiveis(sb, empresa_id, data, duracao, todos_slots)

        if not slots_livres:
            st.warning("Não há horários disponíveis nesta data. Escolha outra data.")
            if st.button("← Voltar", use_container_width=True):
                st.session_state.pub_step = 2
                st.rerun()
            return

        st.markdown(f"**{len(slots_livres)} horário(s) disponível(is):**")

        # Exibir slots em grade de botões (4 por linha)
        slot_selecionado = st.session_state.get("pub_horario_sel")
        cols_por_linha = 4
        for i in range(0, len(slots_livres), cols_por_linha):
            cols = st.columns(cols_por_linha)
            for j, slot in enumerate(slots_livres[i:i + cols_por_linha]):
                hora_fmt = slot.strftime("%H:%M")
                with cols[j]:
                    tipo_btn = "primary" if slot_selecionado == slot.isoformat() else "secondary"
                    if st.button(hora_fmt, key=f"slot_{slot.isoformat()}", use_container_width=True, type=tipo_btn):
                        st.session_state.pub_horario_sel = slot.isoformat()
                        st.rerun()

        col1, col2 = st.columns(2)
        with col1:
            if st.button("← Voltar", use_container_width=True):
                st.session_state.pub_step = 2
                st.rerun()
        with col2:
            if slot_selecionado:
                if st.button("Continuar →", type="primary", use_container_width=True):
                    st.session_state.pub_step = 4
                    st.rerun()
            else:
                st.caption("Selecione um horário acima")

    # ===== PASSO 4: DADOS DO CLIENTE =====
    elif step == 4:
        st.subheader("4️⃣ Seus dados")

        slot_iso = st.session_state.get("pub_horario_sel")
        slot_dt = datetime.fromisoformat(slot_iso) if slot_iso else None
        horario_fmt = slot_dt.strftime("%H:%M") if slot_dt else "—"
        data = st.session_state.get("pub_data", date.today())

        st.caption(
            f"**{st.session_state.get('pub_servico_nome')}** &bull; "
            f"{data.strftime('%d/%m/%Y')} às {horario_fmt}"
        )

        with st.form("form_dados_cliente"):
            nome = st.text_input("Nome completo *", placeholder="Ex: Maria da Silva")
            telefone = st.text_input("Telefone com DDD *", placeholder="Ex: 11999990000")
            email = st.text_input("Email (opcional)", placeholder="seu@email.com")
            confirmar = st.form_submit_button("✅ Confirmar Agendamento", type="primary", use_container_width=True)

        if confirmar:
            # Validação
            tel_limpo = "".join(filter(str.isdigit, telefone))
            if not nome.strip():
                st.error("Nome é obrigatório.")
            elif len(tel_limpo) < 10:
                st.error("Telefone inválido. Informe DDD + número (mínimo 10 dígitos).")
            else:
                # Cadastrar ou recuperar cliente
                cliente_id = _obter_ou_criar_cliente(
                    sb, empresa_id, nome.strip(), tel_limpo, email.strip() or None
                )
                if cliente_id and slot_dt:
                    ok = _salvar_agendamento(
                        sb, empresa_id, cliente_id,
                        st.session_state["pub_servico_id"],
                        slot_dt, st.session_state["pub_duracao"]
                    )
                    if ok:
                        st.session_state.pub_step = 5
                        st.session_state.pub_nome_cliente = nome.strip().title()
                        st.rerun()

        if st.button("← Voltar", use_container_width=True, key="vol_4"):
            st.session_state.pub_step = 3
            st.rerun()

    # ===== PASSO 5: CONFIRMAÇÃO =====
    elif step == 5:
        st.balloons()
        st.success("✅ Agendamento confirmado com sucesso!")

        slot_iso = st.session_state.get("pub_horario_sel")
        slot_dt = datetime.fromisoformat(slot_iso) if slot_iso else None
        data = st.session_state.get("pub_data", date.today())
        horario_fmt = slot_dt.strftime("%H:%M") if slot_dt else "—"
        nome_cliente = st.session_state.get("pub_nome_cliente", "")

        st.markdown(f"""
        <div style="background:#10B98115;border:1px solid #10B981;border-radius:12px;padding:1.5rem;margin:1rem 0">
            <h3 style="color:#10B981">🎉 Resumo do Agendamento</h3>
            <p><b>Salão:</b> {empresa['nome']}</p>
            <p><b>Cliente:</b> {nome_cliente}</p>
            <p><b>Serviço:</b> {st.session_state.get('pub_servico_nome', '—')}</p>
            <p><b>Data:</b> {data.strftime('%d/%m/%Y')}</p>
            <p><b>Horário:</b> {horario_fmt}</p>
            <p style="color:#9CA3AF;font-size:13px">Aguarde a confirmação do salão. Qualquer dúvida, entre em contato diretamente.</p>
        </div>
        """, unsafe_allow_html=True)

        if st.button("➕ Fazer outro agendamento", use_container_width=True, type="primary"):
            # Limpar estado do fluxo
            for key in ["pub_step", "pub_servico_id", "pub_servico_nome", "pub_duracao",
                        "pub_data", "pub_horario_sel", "pub_nome_cliente"]:
                st.session_state.pop(key, None)
            st.rerun()
