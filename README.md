# CFPazziniGil — Sistema de BI

Sistema de Business Intelligence integrado ao ClickUp para o escritório CFPazziniGil.

## Visão Geral

| Camada | Tecnologia | Hospedagem |
|--------|-----------|------------|
| Banco de dados | PostgreSQL (Supabase) | Supabase (gratuito) |
| ETL | Python 3.11 | GitHub Actions (gratuito) |
| Backend API | FastAPI | Railway (~R$25/mês) |
| Frontend | React + Recharts | Vercel (gratuito) |
| Fonte de dados | ClickUp API v2 | — |

---

## Estrutura do Repositório

```
├── supabase/
│   └── schema.sql          ← Executar no Supabase SQL Editor
├── etl/
│   ├── clickup_client.py   ← Cliente ClickUp API v2
│   ├── resolvers.py        ← Match ClickUp ID → BD
│   ├── supabase_writer.py  ← Upsert idempotente
│   ├── run.py              ← Script principal
│   └── requirements.txt
├── .github/
│   └── workflows/
│       └── etl.yml             ← Cron diário 06h UTC
├── backend/
│   ├── main.py             ← FastAPI app
│   ├── db.py               ← Conexão Supabase
│   ├── models.py           ← Modelos Pydantic
│   ├── routers/            ← Endpoints por domínio
│   ├── Dockerfile
│   └── requirements.txt
└── frontend/
    ├── src/
    │   ├── pages/              ← Faturamento, Produtividade, etc.
    │   ├── components/         ← Layout, Card, AlertBadge, etc.
    │   └── lib/                ← api.ts, format.ts
    └── package.json
```

---

## Passo a Passo de Deploy

### 1. Banco de Dados (Supabase)

1. Criar projeto em [supabase.com](https://supabase.com)
2. Ir em **SQL Editor** e executar `supabase/schema.sql` por completo
3. Anotar:
   - **Project URL** (`SUPABASE_URL`)
   - **service_role key** (`SUPABASE_SERVICE_KEY`) — em *Project Settings > API*
   - **anon key** (`SUPABASE_ANON_KEY`)

### 2. Cadastro Inicial de Dados

Executar via Supabase SQL Editor ou insert direto:

```sql
-- Clientes (preencher clickup_list_id com o ID real da List no ClickUp)
INSERT INTO clientes (nome, clickup_list_id) VALUES
  ('Easelabs',      '<list_id_easelabs>'),
  ('SmarttBot',     '<list_id_smarttbot>'),
  ('Posto Urbano',  '<list_id_posto_urbano>');

-- Atualizar clickup_user_id dos colaboradores
UPDATE colaboradores SET clickup_user_id = '<id_real>' WHERE nome = 'Matheus Ferreira';
-- (repetir para Caio, Mara, Amanda, Luciana, Ana Luisa)

-- Contratos
INSERT INTO contratos (cliente_id, modelo, valor_hora, data_inicio)
  SELECT id, 'hora', 500.00, '2026-01-01' FROM clientes WHERE nome = 'Easelabs';
```

### 3. GitHub Secrets

No repositório, ir em *Settings > Secrets and variables > Actions* e criar:

| Secret | Valor |
|--------|-------|
| `CLICKUP_API_TOKEN` | Token do ClickUp (Settings > Apps > API Token) |
| `SUPABASE_URL` | URL do projeto Supabase |
| `SUPABASE_SERVICE_KEY` | service_role key |

### 4. ETL (teste local)

```bash
cd etl
pip install -r requirements.txt
cp ../.env.example .env   # preencher valores reais
python run.py --days 7
```

### 5. Backend (Railway)

1. Criar conta em [railway.app](https://railway.app)
2. **New Project > Deploy from GitHub repo** → selecionar este repositório
3. Definir **Root Directory**: `backend`
4. Adicionar variáveis de ambiente:
   - `SUPABASE_URL`
   - `SUPABASE_SERVICE_KEY`
5. Railway detecta o `Dockerfile` automaticamente
6. Anotar a URL pública gerada (ex: `https://cfpazzinigil-bi.up.railway.app`)

### 6. Frontend (Vercel)

1. Criar conta em [vercel.com](https://vercel.com)
2. **New Project > Import Git Repository** → selecionar este repositório
3. Definir **Root Directory**: `frontend`
4. Adicionar variável de ambiente:
   - `VITE_API_URL` = URL do backend no Railway (ex: `https://cfpazzinigil-bi.up.railway.app`)
5. Deploy automático a cada push no branch `main`

---

## Variáveis de Ambiente

Ver `.env.example` para a lista completa.

---

## Endpoints da API

| Método | Endpoint | Descrição |
|--------|----------|------------|
| GET | `/api/faturamento?mes=YYYY-MM` | Faturamento por cliente |
| GET | `/api/produtividade?mes=YYYY-MM` | Horas por colaborador |
| GET | `/api/rentabilidade?mes=YYYY-MM` | Receita ÷ custo |
| GET | `/api/orcado-vs-realizado?mes=YYYY-MM` | Orçado vs realizado |
| GET | `/api/alertas?mes=YYYY-MM` | Alertas inteligentes |
| GET | `/api/clientes` | Lista de clientes |
| POST | `/api/clientes` | Criar cliente |
| GET | `/api/contratos` | Lista de contratos |
| POST | `/api/contratos` | Criar contrato |
| GET | `/api/etl/status` | Status da última execução |
| POST | `/api/etl/run?days=2` | Disparar ETL manualmente |
| GET | `/api/relatorios/excel?contrato_id=...&mes=YYYY-MM` | Download Excel |
| GET | `/health` | Health check |

Documentação interativa: `https://<seu-backend>/docs`

---

## Modelos de Faturamento

| Modelo | Campo ClickUp `Produto` | Lógica |
|--------|------------------------|--------|
| **Hora** | `Hora` | `Σhoras × valor_hora` |
| **LaaS** | `LaaS` | `valor_fixo_mensal` (fixo) |
| **Escopo Fechado** | `Escopo Fechado` | `valor_escopo` (fixo) + alerta % |

---

## Alertas Gerados

| Tipo | Gatilho | Severidade |
|------|---------|------------|
| `escopo_critico` | Utilização > 80% | warning |
| `escopo_critico` | Utilização > 100% | critical |
| `laas_extrapolado` | Horas > limite LaaS | warning |
| `colabo_abaixo_meta` | Horas < 80% da meta mensal | info |
| `sem_entry` | `time_spent > 0` sem entry individual | warning |

---

## Regras Operacionais Críticas (ClickUp)

- O tempo é sempre registrado na **subtarefa**, nunca na tarefa-mãe
- O ETL consulta sempre pela **tarefa-mãe** (inclui entries das subtarefas automaticamente)
- O campo **Produto** na subtarefa é obrigatório para cálculo — entries sem ele são logadas e excluídas
- Descrições devem usar substantivos: “Elaboração de minuta” (não “Elaborar minuta”)
