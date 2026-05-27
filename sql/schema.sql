-- ================================================================
-- AgendaPro — Schema completo do banco de dados Supabase
-- Prefixo obrigatório: agd_ (evita conflitos com outros sistemas)
-- Execute este SQL no painel do Supabase: SQL Editor
-- ================================================================

-- ================================================================
-- 1. TABELAS
-- ================================================================

-- Empresas (salões) cadastradas na plataforma
CREATE TABLE IF NOT EXISTS agd_empresas (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    nome         TEXT NOT NULL,
    slug         TEXT UNIQUE NOT NULL,       -- ex: "studio-bella" — usado na URL pública
    telefone     TEXT,
    endereco     TEXT,
    logo_url     TEXT,
    cor_primaria TEXT DEFAULT '#8B5CF6',     -- cor do tema do salão
    criado_em    TIMESTAMPTZ DEFAULT now()
);

-- Perfis: vínculo entre usuário do Supabase Auth e empresa
CREATE TABLE IF NOT EXISTS agd_perfis (
    id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id    UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    empresa_id UUID NOT NULL REFERENCES agd_empresas(id) ON DELETE CASCADE,
    nome       TEXT,
    UNIQUE(user_id)
);

-- Configurações de funcionamento do salão
CREATE TABLE IF NOT EXISTS agd_configuracoes (
    id                   UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    empresa_id           UUID NOT NULL REFERENCES agd_empresas(id) ON DELETE CASCADE,
    dias_funcionamento   INTEGER[] DEFAULT '{1,2,3,4,5,6}', -- 0=Dom, 1=Seg... 6=Sáb
    hora_abertura        TIME DEFAULT '08:00',
    hora_fechamento      TIME DEFAULT '18:00',
    intervalo_minutos    INTEGER DEFAULT 30,                  -- granularidade dos slots (30 ou 60)
    tempo_almoco_inicio  TIME,
    tempo_almoco_fim     TIME,
    mensagem_confirmacao TEXT,                                -- mensagem padrão de lembrete
    UNIQUE(empresa_id)
);

-- Serviços oferecidos pelo salão
CREATE TABLE IF NOT EXISTS agd_servicos (
    id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    empresa_id       UUID NOT NULL REFERENCES agd_empresas(id) ON DELETE CASCADE,
    nome             TEXT NOT NULL,
    duracao_minutos  INTEGER NOT NULL,    -- ex: 30, 60, 90, 120
    preco            NUMERIC(10,2),       -- opcional
    retorno_dias     INTEGER,             -- dias sugeridos para retorno (ex: 35 para coloração)
    ativo            BOOLEAN DEFAULT true,
    criado_em        TIMESTAMPTZ DEFAULT now()
);

-- Clientes do salão
CREATE TABLE IF NOT EXISTS agd_clientes (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    empresa_id   UUID NOT NULL REFERENCES agd_empresas(id) ON DELETE CASCADE,
    nome         TEXT NOT NULL,
    telefone     TEXT NOT NULL,
    email        TEXT,
    observacoes  TEXT,
    criado_em    TIMESTAMPTZ DEFAULT now(),
    UNIQUE(empresa_id, telefone)           -- mesmo cliente não duplica por telefone
);

-- Agendamentos
CREATE TABLE IF NOT EXISTS agd_agendamentos (
    id                    UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    empresa_id            UUID NOT NULL REFERENCES agd_empresas(id) ON DELETE CASCADE,
    cliente_id            UUID NOT NULL REFERENCES agd_clientes(id),
    servico_id            UUID NOT NULL REFERENCES agd_servicos(id),
    data_hora_inicio      TIMESTAMPTZ NOT NULL,
    data_hora_fim         TIMESTAMPTZ NOT NULL,  -- calculado: inicio + duracao_minutos
    status                TEXT DEFAULT 'pendente'
                              CHECK (status IN ('pendente','confirmado','concluido','cancelado')),
    observacoes           TEXT,
    lembrete_enviado      BOOLEAN DEFAULT false,
    data_retorno_sugerida DATE,                  -- preenchida quando status = 'concluido'
    criado_em             TIMESTAMPTZ DEFAULT now()
);

-- Bloqueios de horários e dias
CREATE TABLE IF NOT EXISTS agd_bloqueios (
    id                     UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    empresa_id             UUID NOT NULL REFERENCES agd_empresas(id) ON DELETE CASCADE,
    tipo                   TEXT NOT NULL
                               CHECK (tipo IN ('dia_inteiro','horario_especifico','recorrente_semanal')),
    data                   DATE,           -- para dia_inteiro e horario_especifico
    hora_inicio            TIME,           -- para horario_especifico
    hora_fim               TIME,           -- para horario_especifico
    dia_semana             INTEGER,        -- 0-6 para recorrente_semanal (0=Dom)
    hora_inicio_recorrente TIME,           -- para recorrente_semanal
    hora_fim_recorrente    TIME,           -- para recorrente_semanal
    motivo                 TEXT,
    criado_em              TIMESTAMPTZ DEFAULT now()
);

-- ================================================================
-- 2. ROW LEVEL SECURITY (RLS)
-- ================================================================

ALTER TABLE agd_empresas      ENABLE ROW LEVEL SECURITY;
ALTER TABLE agd_perfis        ENABLE ROW LEVEL SECURITY;
ALTER TABLE agd_configuracoes ENABLE ROW LEVEL SECURITY;
ALTER TABLE agd_servicos      ENABLE ROW LEVEL SECURITY;
ALTER TABLE agd_clientes      ENABLE ROW LEVEL SECURITY;
ALTER TABLE agd_agendamentos  ENABLE ROW LEVEL SECURITY;
ALTER TABLE agd_bloqueios     ENABLE ROW LEVEL SECURITY;

-- Função auxiliar: retorna o empresa_id do usuário logado
-- SECURITY DEFINER: executa com privilégios do criador, não do chamador
CREATE OR REPLACE FUNCTION agd_get_empresa_id()
RETURNS UUID AS $$
    SELECT empresa_id FROM agd_perfis WHERE user_id = auth.uid() LIMIT 1;
$$ LANGUAGE sql STABLE SECURITY DEFINER;

-- ----------------------------------------------------------------
-- Políticas: agd_empresas
-- ----------------------------------------------------------------
-- Leitura pública (necessária para busca por slug na página de agendamento)
CREATE POLICY "publico_select_empresas" ON agd_empresas
    FOR SELECT USING (true);

-- Dono da empresa pode atualizar seus dados
CREATE POLICY "empresa_update_empresas" ON agd_empresas
    FOR UPDATE USING (id = agd_get_empresa_id());

-- ----------------------------------------------------------------
-- Políticas: agd_perfis
-- ----------------------------------------------------------------
CREATE POLICY "select_own_perfil" ON agd_perfis
    FOR SELECT USING (user_id = auth.uid());

-- ----------------------------------------------------------------
-- Políticas: agd_configuracoes
-- ----------------------------------------------------------------
-- Leitura pública (usada pela página de agendamento para calcular slots)
CREATE POLICY "publico_select_configuracoes" ON agd_configuracoes
    FOR SELECT USING (true);

CREATE POLICY "empresa_insert_configuracoes" ON agd_configuracoes
    FOR INSERT WITH CHECK (empresa_id = agd_get_empresa_id());

CREATE POLICY "empresa_update_configuracoes" ON agd_configuracoes
    FOR UPDATE USING (empresa_id = agd_get_empresa_id());

-- ----------------------------------------------------------------
-- Políticas: agd_servicos
-- ----------------------------------------------------------------
-- Leitura pública (listagem de serviços na página de agendamento)
CREATE POLICY "publico_select_servicos" ON agd_servicos
    FOR SELECT USING (true);

CREATE POLICY "empresa_insert_servicos" ON agd_servicos
    FOR INSERT WITH CHECK (empresa_id = agd_get_empresa_id());

CREATE POLICY "empresa_update_servicos" ON agd_servicos
    FOR UPDATE USING (empresa_id = agd_get_empresa_id());

CREATE POLICY "empresa_delete_servicos" ON agd_servicos
    FOR DELETE USING (empresa_id = agd_get_empresa_id());

-- ----------------------------------------------------------------
-- Políticas: agd_clientes
-- ----------------------------------------------------------------
-- Leitura pública (verificar se cliente já existe pelo telefone)
CREATE POLICY "publico_select_clientes" ON agd_clientes
    FOR SELECT USING (true);

-- Inserção pública (cliente se cadastra ao agendar)
CREATE POLICY "publico_insert_clientes" ON agd_clientes
    FOR INSERT WITH CHECK (true);

-- Atualização apenas pelo dono da empresa
CREATE POLICY "empresa_update_clientes" ON agd_clientes
    FOR UPDATE USING (empresa_id = agd_get_empresa_id());

CREATE POLICY "empresa_delete_clientes" ON agd_clientes
    FOR DELETE USING (empresa_id = agd_get_empresa_id());

-- ----------------------------------------------------------------
-- Políticas: agd_agendamentos
-- ----------------------------------------------------------------
-- Leitura pública (verificar conflitos de horário ao agendar)
CREATE POLICY "publico_select_agendamentos" ON agd_agendamentos
    FOR SELECT USING (true);

-- Inserção pública (cliente agenda sem login)
CREATE POLICY "publico_insert_agendamentos" ON agd_agendamentos
    FOR INSERT WITH CHECK (true);

-- Atualização e exclusão apenas pelo dono da empresa
CREATE POLICY "empresa_update_agendamentos" ON agd_agendamentos
    FOR UPDATE USING (empresa_id = agd_get_empresa_id());

CREATE POLICY "empresa_delete_agendamentos" ON agd_agendamentos
    FOR DELETE USING (empresa_id = agd_get_empresa_id());

-- ----------------------------------------------------------------
-- Políticas: agd_bloqueios
-- ----------------------------------------------------------------
-- Leitura pública (verificar bloqueios ao gerar slots disponíveis)
CREATE POLICY "publico_select_bloqueios" ON agd_bloqueios
    FOR SELECT USING (true);

CREATE POLICY "empresa_insert_bloqueios" ON agd_bloqueios
    FOR INSERT WITH CHECK (empresa_id = agd_get_empresa_id());

CREATE POLICY "empresa_update_bloqueios" ON agd_bloqueios
    FOR UPDATE USING (empresa_id = agd_get_empresa_id());

CREATE POLICY "empresa_delete_bloqueios" ON agd_bloqueios
    FOR DELETE USING (empresa_id = agd_get_empresa_id());

-- ================================================================
-- 3. ÍNDICES (melhoram performance das queries mais comuns)
-- ================================================================

CREATE INDEX IF NOT EXISTS idx_agd_agendamentos_empresa_data
    ON agd_agendamentos(empresa_id, data_hora_inicio);

CREATE INDEX IF NOT EXISTS idx_agd_agendamentos_status
    ON agd_agendamentos(empresa_id, status);

CREATE INDEX IF NOT EXISTS idx_agd_agendamentos_retorno
    ON agd_agendamentos(empresa_id, data_retorno_sugerida)
    WHERE data_retorno_sugerida IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_agd_clientes_telefone
    ON agd_clientes(empresa_id, telefone);

CREATE INDEX IF NOT EXISTS idx_agd_servicos_empresa_ativo
    ON agd_servicos(empresa_id, ativo);

-- ================================================================
-- 4. DADOS DE DEMONSTRAÇÃO
-- ================================================================
-- ATENÇÃO: Substitua o empresa_id abaixo pelo UUID real após criar sua conta.
-- Passos:
--   1. Crie uma conta em Authentication > Users no painel do Supabase
--   2. Insira manualmente um registro em agd_empresas com seu slug
--   3. Insira um registro em agd_perfis vinculando user_id ao empresa_id
--   4. Acesse o painel e configure horários e serviços pelo próprio sistema

-- Empresa de demonstração (inserir manualmente, sem empresa_id ainda)
INSERT INTO agd_empresas (nome, slug, telefone, cor_primaria)
VALUES ('Studio Bella', 'studio-bella', '17999990000', '#8B5CF6')
ON CONFLICT (slug) DO NOTHING;

-- Após criar empresa e perfil, adicione serviços de exemplo via painel:
--   Corte Feminino      — 60 min — R$ 80,00  — retorno 45 dias
--   Coloração           — 120 min — R$ 200,00 — retorno 35 dias
--   Escova Progressiva  — 180 min — R$ 350,00 — retorno 90 dias
--   Corte Masculino     — 30 min — R$ 40,00   — retorno 30 dias
--   Manicure            — 45 min — R$ 35,00   — retorno 21 dias
