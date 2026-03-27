-- =============================================================
-- CFPazziniGil — BI System Schema
-- Executar no Supabase SQL Editor
-- =============================================================

-- Extensões necessárias
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- =============================================================
-- CLIENTES
-- =============================================================
CREATE TABLE IF NOT EXISTS clientes (
    id                UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    nome              TEXT        NOT NULL,
    cnpj              TEXT,
    contato_nome      TEXT,
    contato_email     TEXT,
    ativo             BOOLEAN     DEFAULT true,
    clickup_list_id   TEXT,           -- ID da lista no ClickUp para auto-match
    created_at        TIMESTAMPTZ DEFAULT now()
);

COMMENT ON TABLE clientes IS 'Clientes do escritório. clickup_list_id é usado pelo ETL para resolução automática.';
COMMENT ON COLUMN clientes.clickup_list_id IS 'ID da List no ClickUp que corresponde a este cliente.';

-- =============================================================
-- COLABORADORES
-- =============================================================
CREATE TABLE IF NOT EXISTS colaboradores (
    id                  UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    nome                TEXT        NOT NULL,
    clickup_user_id     TEXT        UNIQUE,     -- match automático com time entries
    valor_hora_custo    NUMERIC(10,2),          -- custo interno (não faturamento)
    meta_horas_mes      INT         DEFAULT 160, -- meta mensal em horas
    ativo               BOOLEAN     DEFAULT true,
    created_at          TIMESTAMPTZ DEFAULT now()
);

COMMENT ON TABLE colaboradores IS 'Membros do escritório. clickup_user_id é usado pelo ETL para match de time entries.';

-- =============================================================
-- CONTRATOS
-- =============================================================
CREATE TABLE IF NOT EXISTS contratos (
    id                  UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    cliente_id          UUID        REFERENCES clientes(id) ON DELETE RESTRICT,
    modelo              TEXT        NOT NULL CHECK (modelo IN ('hora', 'laas', 'escopo_fechado')),
    descricao           TEXT,
    -- Campos específicos por modelo --
    valor_hora          NUMERIC(10,2),          -- modelo 'hora'
    valor_fixo_mensal   NUMERIC(10,2),          -- modelo 'laas'
    horas_laas_limite   INT,                    -- modelo 'laas': alerta de extrapolação
    valor_escopo        NUMERIC(10,2),          -- modelo 'escopo_fechado'
    horas_escopo        INT,                    -- modelo 'escopo_fechado'
    -- Vigência --
    data_inicio         DATE        NOT NULL,
    data_fim            DATE,
    status              TEXT        DEFAULT 'ativo' CHECK (status IN ('ativo', 'encerrado', 'suspenso')),
    created_at          TIMESTAMPTZ DEFAULT now()
);

COMMENT ON TABLE contratos IS 'Contratos dos clientes. O campo modelo determina a lógica de faturamento.';
COMMENT ON COLUMN contratos.modelo IS 'hora | laas | escopo_fechado';
COMMENT ON COLUMN contratos.horas_laas_limite IS 'Limite mensal de horas antes de disparar alerta para LaaS.';
COMMENT ON COLUMN contratos.horas_escopo IS 'Total de horas contratadas para escopo fechado.';

-- =============================================================
-- TIME ENTRIES (populado automaticamente pelo ETL)
-- =============================================================
CREATE TABLE IF NOT EXISTS time_entries (
    id                  UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    clickup_entry_id    TEXT        UNIQUE,         -- ID nativo do ClickUp (garante idempotência)
    clickup_task_id     TEXT,
    clickup_user_id     TEXT,
    colaborador_id      UUID        REFERENCES colaboradores(id),
    cliente_id          UUID        REFERENCES clientes(id),
    contrato_id         UUID        REFERENCES contratos(id),
    -- Dados da atividade --
    tarefa_nome         TEXT,
    descricao           TEXT,
    providencia         TEXT,       -- Elaboração | Análise | Reunião | ...
    demanda_legal       TEXT,       -- Rotina Societária | Contratos | ...
    produto             TEXT,       -- Hora | LaaS | Escopo Fechado
    -- Tempo --
    data                DATE        NOT NULL,
    duracao_minutos     INT         NOT NULL,
    mes_referencia      TEXT,       -- 'YYYY-MM' para agrupamento rápido
    -- Controle --
    importado_em        TIMESTAMPTZ DEFAULT now(),
    alerta_sem_entry    BOOLEAN     DEFAULT false    -- flag do erro crítico de registro
);

CREATE INDEX IF NOT EXISTS idx_time_entries_mes ON time_entries (mes_referencia);
CREATE INDEX IF NOT EXISTS idx_time_entries_cliente ON time_entries (cliente_id);
CREATE INDEX IF NOT EXISTS idx_time_entries_colaborador ON time_entries (colaborador_id);
CREATE INDEX IF NOT EXISTS idx_time_entries_contrato ON time_entries (contrato_id);

COMMENT ON TABLE time_entries IS 'Horas trabalhadas importadas do ClickUp. Populado pelo ETL diário.';
COMMENT ON COLUMN time_entries.clickup_entry_id IS 'ID único do time entry no ClickUp. Usado para upsert idempotente.';
COMMENT ON COLUMN time_entries.alerta_sem_entry IS 'true quando task.time_spent > 0 mas sem entries individuais (erro de registro manual).';

-- =============================================================
-- FATURAS
-- =============================================================
CREATE TABLE IF NOT EXISTS faturas (
    id                  UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    contrato_id         UUID        REFERENCES contratos(id) ON DELETE RESTRICT,
    mes_referencia      TEXT        NOT NULL,        -- 'YYYY-MM'
    valor_calculado     NUMERIC(10,2),               -- calculado pelo sistema
    valor_emitido       NUMERIC(10,2),               -- após ajustes manuais
    status              TEXT        DEFAULT 'calculado'
                            CHECK (status IN ('calculado', 'emitido', 'pago', 'cancelado')),
    data_emissao        DATE,
    data_pagamento      DATE,
    observacoes         TEXT,
    created_at          TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_faturas_mes ON faturas (mes_referencia);
CREATE INDEX IF NOT EXISTS idx_faturas_status ON faturas (status);

COMMENT ON TABLE faturas IS 'Pipeline de recebíveis. Transição: calculado → emitido → pago.';

-- =============================================================
-- ORÇAMENTOS
-- =============================================================
CREATE TABLE IF NOT EXISTS orcamentos (
    id                  UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    cliente_id          UUID        REFERENCES clientes(id) ON DELETE RESTRICT,
    mes_referencia      TEXT        NOT NULL,        -- 'YYYY-MM'
    horas_previstas     INT,
    receita_prevista    NUMERIC(10,2),
    created_at          TIMESTAMPTZ DEFAULT now(),
    UNIQUE (cliente_id, mes_referencia)
);

COMMENT ON TABLE orcamentos IS 'Orçamento mensal por cliente. Usado na visão Orçado vs Realizado.';

-- =============================================================
-- LOG DE EXECUÇÕES DO ETL
-- =============================================================
CREATE TABLE IF NOT EXISTS etl_log (
    id                  UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    executado_em        TIMESTAMPTZ DEFAULT now(),
    status              TEXT,           -- 'success' | 'error'
    entries_importadas  INT,
    entries_alertas     INT,
    detalhes            JSONB
);

CREATE INDEX IF NOT EXISTS idx_etl_log_executado ON etl_log (executado_em DESC);

COMMENT ON TABLE etl_log IS 'Log de cada execução do ETL. Inclui alertas de dados incompletos.';

-- =============================================================
-- DADOS INICIAIS — Equipe CFPazziniGil
-- Executar após criar as tabelas
-- =============================================================

INSERT INTO colaboradores (nome, clickup_user_id, meta_horas_mes) VALUES
    ('Rafael Gil de Lima Bernardes', '3163101',  160),
    ('Sara Pazzini',                 '81948576', 160),
    ('Matheus Ferreira',             NULL,       160),
    ('Caio Franco',                  NULL,       160),
    ('Mara Assis',                   NULL,       160),
    ('Amanda Ventura Araujo',        NULL,       160),
    ('Luciana Cruz Nascimento',      NULL,       160),
    ('Ana Luisa Castro',             NULL,       160)
ON CONFLICT (clickup_user_id) DO NOTHING;

-- Atenção: preencher os clickup_user_id NULL após obter os IDs reais do ClickUp.
-- Executar: SELECT id, nome FROM workspace_members (via MCP ou API)
