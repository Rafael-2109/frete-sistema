# Sistema de Fretes — Referencia Compartilhada

**Ultima Atualizacao**: 01/06/2026

> Este CLAUDE.md e lido por AMBOS os contextos (Claude Code dev + Agent SDK web).
> Conteudo dev-only (Quick Start, CSS, migrations) esta em `~/.claude/CLAUDE.md`.

---

## TECH STACK

> Verificado em 13/05/2026 (local Python 3.12.3 / Node 22.17 + Render workspace `tea-d01amimuk2gs73dhlup0`).
> Versoes exatas: `requirements.txt`, `package.json`. Detalhes infra: `.claude/references/INFRAESTRUTURA.md`.

| Camada | Stack |
|--------|-------|
| **Infra (Render, Oregon)** | Web `sistema-fretes` (Pro Plus) · Worker `sistema-fretes-worker-atacadao` (Standard, RQ) · Postgres 18 `sistema-fretes-db` (Basic 4GB) · Redis 8.1 `sistema-fretes-redis` (Starter, `allkeys_lru`) |
| **Backend** | Python 3.12 · **Flask 3.1.2** · Flask-SQLAlchemy 3.1 · Flask-Login 0.6 · Flask-Migrate 4.1 · Flask-WTF 1.2 · SQLAlchemy 2.0 · Gunicorn 25 + gevent · psycopg2 + asyncpg (pool async SessionStore) · Pydantic 2.12 · FastAPI 0.129 (endpoints isolados) |
| **Workers / Async** | RQ 2.6 · Redis 7.2 (client) · APScheduler · 3 perfis de worker (light-reserved / full / general — anti-starvation) |
| **AI / Agente** | Anthropic SDK 0.98.1 · Claude Agent SDK 0.2.87 (CLI 2.1.150) · MCP 1.26 · Voyage AI + pgvector (embeddings) |
| **Frontend** | **HTML5 + Jinja2** (templates) · **Bootstrap 5.3.3** (CSS self-hosted via `@layer bootstrap`, JS bundle CDN) · **jQuery 3.6** + jQuery Mask 1.14 (legado) · **HTMX 1.9.11** · Vanilla JS · CSS `@layer` proprio (tokens → base → components → modules → utilities) · **FontAwesome 6.4.0** (CDN) |
| **Artifacts (chat web)** | React 18 + TS + Tailwind + Parcel via Node 20 (NVM lazy install no worker) · bundle.html servido em iframe sandboxed |
| **Mobile App (GPS)** | Capacitor 6 (Android/iOS) — modulo rastreamento de motoristas |
| **Browser Automation** | Playwright 1.58 (Chromium — SSW, Atacadao Hodie Booking) · Selenium 4.40 (legado) |
| **Storage** | AWS S3 via boto3 1.42 — screenshots, archives sessao, artifacts, anexos devolucao |
| **Observability** | Sentry SDK 2.54 (errors + APM) · structlog · colorlog |
| **Data / Files** | pandas 3.0 · openpyxl · xlsxwriter · pdfplumber + pypdf · weasyprint · python-docx · tesserocr (OCR PT) |
| **Integracoes externas** | Odoo XML-RPC (ERP CIEL IT) · Microsoft Teams Bot Framework · WhatsApp via OpenClaw (Baileys) · Pluggy Open Finance (Bradesco) |
| **Build / Deploy** | `build.sh` + `start_render.sh` (web) · `start_worker_render.sh` (worker) · auto-deploy via `main` branch GitHub |

---

## DADOS:

### OBRIGATÓRIO
1. **FONTE PARA CONSULTA**: Utilize exclusivamente o MCP do Render, orientações em: `.claude/references/INFRAESTRUTURA.md`
2. **NÃO UTILIZAR**: Dados locais = Dados teste.
3. **CROSS-VERIFICACAO ODOO**: Se o usuario pedir para verificar no Odoo, seguir roteamento em `.claude/references/odoo/ROUTING_ODOO.md`. Se encontrar inconsistencias em dados locais/Render originados do Odoo, TAMBEM verificar direto no Odoo.


## REGRAS UNIVERSAIS

### SEMPRE:
1. **AMBIENTE VIRTUAL**: `source .venv/bin/activate` quando executar scripts Python
2. **FONTE DE DADOS/DADOS DE PRODUÇÃO**: ANTES de consultar dados reais, metricas, logs ou deploys: LER `.claude/references/INFRAESTRUTURA.md`
3. **TIMEZONE**: ANTES de escrever qualquer codigo com datas/timestamps: LER `.claude/references/REGRAS_TIMEZONE.md`.

---

## FORMATACAO NUMERICA BRASILEIRA

Filtros em `app/utils/template_filters.py`:
```jinja
{{ valor|valor_br }}        {# R$ 1.234,56 #}
{{ valor|valor_br(4) }}     {# R$ 1.234,5678 #}
{{ qtd|numero_br }}         {# 1.234,567 #}
{{ qtd|numero_br(0) }}      {# 1.234 #}
```

---

## MODELOS CRITICOS

**Campos de tabelas**: SEMPRE usar schemas auto-gerados em `.claude/skills/consultando-sql/schemas/tables/{tabela}.json`
References contem APENAS regras de negocio, NAO campos.

**ANTES de usar CarteiraPrincipal/Separacao**: LER `.claude/references/modelos/REGRAS_CARTEIRA_SEPARACAO.md`
**ANTES de usar Embarque/Faturamento/etc.**: LER `.claude/references/modelos/REGRAS_MODELOS.md`
**ANTES de executar qualquer skill ou operacao Odoo**: LER `.claude/references/ROUTING_SKILLS.md`
**ANTES de criar/editar doc ou script**: LER `.claude/references/ARQUITETURA_DE_ARTEFATOS.md` (padrao PAD-A) ou usar skill `padronizando-docs`.

Gotchas rapidos:
- CarteiraPrincipal: `qtd_saldo_produto_pedido` (NAO `qtd_saldo`)
- Separacao: `qtd_saldo` (NAO `qtd_saldo_produto_pedido`)
- Separacao tem `expedicao`, `agendamento`, `protocolo` (Carteira NAO tem)

---

## INDICE DE REFERENCIAS

> Indice unico consultado por AMBOS os contextos.
> Entradas dev-only (CSS, Best Practices, MCP Capabilities, CLAUDE.md de modulo) estao em `~/.claude/CLAUDE.md`.

### Modelos e Regras de Negocio

| Preciso de... | Documento |
|---------------|-----------|
| Regras CarteiraPrincipal / Separacao | `.claude/references/modelos/REGRAS_CARTEIRA_SEPARACAO.md` |
| Regras Embarque, Faturamento, etc. | `.claude/references/modelos/REGRAS_MODELOS.md` |
| Campos de QUALQUER tabela | `.claude/skills/consultando-sql/schemas/tables/{tabela}.json` |
| Cadeia Pedido -> Entrega | `.claude/references/modelos/CADEIA_PEDIDO_ENTREGA.md` |
| Queries SQL / JOINs | `.claude/references/modelos/QUERIES_MAPEAMENTO.md` |
| Regras de negocio | `.claude/references/negocio/REGRAS_NEGOCIO.md` |
| Prioridades P1-P7 e envio parcial | `.claude/references/negocio/REGRAS_P1_P7.md` |
| Frete Real vs Teorico | `.claude/references/negocio/FRETE_REAL_VS_TEORICO.md` |
| Margem e Custeio | `.claude/references/negocio/MARGEM_CUSTEIO.md` |

### Odoo

| Preciso de... | Documento |
|---------------|-----------|
| Odoo routing (regra zero, skills) | `.claude/references/odoo/ROUTING_ODOO.md` |
| Odoo modelos e campos (CIEL IT) | `.claude/references/odoo/MODELOS_CAMPOS.md` |
| Pipeline recebimento (4 fases) | `.claude/references/odoo/PIPELINE_RECEBIMENTO.md` |
| IDs fixos (company, journal, picking_type) | `.claude/references/odoo/IDS_FIXOS.md` |
| Gotchas Odoo (timeouts, erros) | `.claude/references/odoo/GOTCHAS.md` |
| Fluxos de reconciliacao financeira | `app/financeiro/FLUXOS_RECONCILIACAO.md` |

### SSW e CarVia

| Preciso de... | Documento |
|---------------|-----------|
| SSW indice geral | `.claude/references/ssw/INDEX.md` |
| SSW routing (decision tree) | `.claude/references/ssw/ROUTING_SSW.md` |
| CarVia status de adocao | `.claude/references/ssw/CARVIA_STATUS.md` |
| Portal Atacadao (automacao Hodie Booking) | `.claude/skills/operando-portal-atacadao/SKILL.md` |

### Infraestrutura e Agente

| Preciso de... | Documento |
|---------------|-----------|
| Timezone (convencao Brasil naive) | `.claude/references/REGRAS_TIMEZONE.md` |
| Routing de skills | `.claude/references/ROUTING_SKILLS.md` |
| Infraestrutura Render | `.claude/references/INFRAESTRUTURA.md` |
| Confiabilidade de subagentes | `.claude/references/SUBAGENT_RELIABILITY.md` (M1.1: SDK 0.1.60+ via `subagent_reader.get_subagent_findings` primario, `/tmp/` fallback) |
| Protocolo de memoria (agente) | `.claude/references/MEMORY_PROTOCOL.md` |
| Regras de output complementares (I1, I5, I6) | `.claude/references/REGRAS_OUTPUT.md` |
| Estudo system prompts 2026 (best practices + pre-mortem + red team) | `.claude/references/STUDY_PROMPT_ENGINEERING_2026.md` |
| Quality review do system_prompt.md v4.2.0 (score + findings) | `.claude/references/STUDY_PROMPT_ENGINEERING_2026_QUALITY_REVIEW.md` |
| Roadmap prompt engineering 2026 (R1-R17, P0-P3) | `.claude/references/ROADMAP_PROMPT_ENGINEERING_2026.md` |
| Prompt injection hardening (defense in depth) | `.claude/references/PROMPT_INJECTION_HARDENING.md` |
| S3 storage (arquivos persistidos — todos modulos) | `.claude/references/S3_STORAGE.md` |
| Indice completo | `.claude/references/INDEX.md` |
| Documentacao tecnica (arvore docs/) | `docs/INDEX.md` |

### Design System (UI/CSS)

| Preciso de... | Documento |
|---------------|-----------|
| Badges, botoes, tabelas (qual classe usar, como criar nova) | `.claude/references/design/GUIA_COMPONENTES_UI.md` |
| Arquitetura CSS (@layer, tokens, components/modules) | `app/static/css/README.md` |
| Auditar codigo existente | `python scripts/audits/ui_audit.py` |
| Detectar regressao antes de commit em CSS/templates | `python scripts/audits/ui_audit_regression.py` |
| **Lint policy bloqueador** (regras P1-P9) | `python scripts/audits/ui_policy_lint.py --enforce-new` (pre-commit) ou `--report-only` (auditoria) |
| Pre-commit hook UI lint (instalar) | `ln -sf ../../scripts/hooks/pre-commit-ui-lint.sh .git/hooks/pre-commit && chmod +x .git/hooks/pre-commit` |
| Analise dimensional (WCAG, headers, etc) | `python scripts/audits/ui_dimension_analysis.py` → `relatorios/ui_dimension_analysis_<data>.md` |
| Detectar regressao VISUAL (pixel diff) antes de commit | `tests/visual/` (capture + compare via Playwright/PIL) |
| Visual regression — credenciais bot | `scripts/seed/create_visual_test_user.py` (cria/atualiza `claude-visual@bot.nacom.com.br`, salva senha so em `.env` — NUNCA commitar) |
| Catalogo de inconsistencias (badges duplicados, tabelas, vars BS) | `relatorios/ui_audit_FINDINGS_<data>.md` |

---

## CAMINHOS DO SISTEMA

| Modulo | Caminhos corretos |
|--------|-------------------|
| Carteira de Pedidos | `app/carteira/routes/`, `app/carteira/services/`, `app/carteira/utils/`, `app/templates/carteira/` — ver `app/carteira/CLAUDE.md` |
| Agente Web | `app/agente/` (Claude Agent SDK) — ver `app/agente/CLAUDE.md` (+ `app/agente/services/CLAUDE.md`) |
| Agente Lojas HORA | `app/agente_lojas/` (Claude Agent SDK isolado, endpoint `/agente-lojas/*`) — ver `app/agente_lojas/CLAUDE.md` |
| Chat in-app | `app/chat/routes/`, `app/chat/services/`, `app/templates/chat/` — ver `app/chat/CLAUDE.md` |
| Lojas HORA (Motochefe) | `app/hora/routes/`, `app/hora/services/`, `app/hora/models/`, `app/templates/hora/` — ver `app/hora/CLAUDE.md` |
| Motos Assai (B2B Q.P.A.) | `app/motos_assai/routes/`, `app/motos_assai/services/`, `app/motos_assai/models/`, `app/templates/motos_assai/` — ver `app/motos_assai/CLAUDE.md` |
| Financeiro | `app/financeiro/routes/`, `app/financeiro/services/`, `app/financeiro/workers/` — ver `app/financeiro/CLAUDE.md` |
| Odoo | `app/odoo/services/`, `app/odoo/utils/`, `app/odoo/jobs/` — ver `app/odoo/CLAUDE.md` |
| CarVia | `app/carvia/routes/`, `app/carvia/services/`, `app/templates/carvia/` — ver `app/carvia/CLAUDE.md` |
| Seguranca | `app/seguranca/routes/`, `app/seguranca/services/`, `app/templates/seguranca/` — ver `app/seguranca/CLAUDE.md` |
| Teams Bot | `app/teams/` — ver `app/teams/CLAUDE.md` |
| WhatsApp Bot | `app/whatsapp/` (canal via OpenClaw + plugin nacom-bridge) — ver `app/whatsapp/CLAUDE.md` |
| Fretes | `app/fretes/routes.py`, `app/fretes/services/`, `app/templates/fretes/` — ver `app/fretes/CLAUDE.md` |
| Recebimento | `app/recebimento/routes/`, `app/recebimento/services/`, `app/recebimento/workers/` |
| Devolucao | `app/devolucao/routes/`, `app/devolucao/services/` — ver `app/devolucao/CLAUDE.md` (dev) ou `app/devolucao/README.md` (narrativa) |
| Pallet | `app/pallet/routes/`, `app/pallet/services/`, `app/templates/pallet/` |
| Producao | `app/producao/routes.py`, `app/producao/models.py` |
| Pedidos | `app/pedidos/routes/`, `app/pedidos/services/`, `app/pedidos/workers/` |
| **NAO ESTENDER** | `app/carteira/main_routes.py` — apenas dashboard `index()` (Fase 3 limpa). Novas rotas: usar `app/carteira/routes/` |

> Para lista completa de modulos e rotas: `.claude/references/INDEX.md`

---

## SUBAGENTES

| Agent | Quando Usar |
|-------|-------------|
| `analista-carteira` | Analise P1-P7, comunicacao PCP/Comercial |
| `especialista-odoo` | Problema cross-area Odoo |
| `raio-x-pedido` | Visao 360 do pedido |
| `desenvolvedor-integracao-odoo` | Criar/modificar integracoes Odoo (dev-only, nao exposto ao agente web) |
| `gestor-carvia` | Operacoes CarVia cross-dimensional (ops + entregas + frete) |
| `gestor-ssw` | Operacoes SSW multi-step (POP-A10, cadastros) |
| `auditor-financeiro` | Reconciliacao financeira, auditoria Local vs Odoo, SEM_MATCH |
| `controlador-custo-frete` | Custo real frete, divergencia CTe, conta corrente transportadoras |
| `gestor-recebimento` | Pipeline recebimento 4 fases, DFEs bloqueados, troubleshooting |
| `gestor-devolucoes` | Devolucoes NFD, De-Para AI, descarte vs retorno |
| `gestor-estoque-producao` | Ruptura, estoque comprometido, producao vs programada (READ-ONLY) |
| `gestor-estoque-odoo` | Operacoes de **escrita** de estoque no Odoo + consulta AO VIVO: skills atomicas `ajustando-quant-odoo` (✅ MATURADA), `transferindo-interno-odoo` (🟡 min viavel — lote↔lote mesma loc OU loc↔loc mesmo lote intra-empresa OU MIGRACAO↔Indisponivel via MODO C; delegacao a ajustar_quant 2x com delta_esperado propagado; G021/G022/G027/G031 codificados), `operando-reservas-odoo` (🟡 min viavel — cirurgia/cancelamento de MLs orfas), `operando-picking-odoo` (🟡 min viavel — cancelar/validar/devolver picking generico; **invariante G019/G020 codificada** — ONDA 0.4 ✅ fechada), `operando-mo-odoo` (🟡 min viavel NOVA 2026-05-24 v5 — cancelar MO single ou batch; guard G-MO-01 furo contabil + idempotencia action_cancel validada), `consultando-quant-odoo` (🟡 READ-only ao vivo, auditoria pos-WRITE), `escriturando-odoo` (🟡 ABRANGENTE 10 atomos LIVE v19+, ENTRADA DFe/NF), `faturando-odoo` (🟡 ATOMICA 5 atomos LIVE v24+, SAIDA account.move; pipeline A-F via orchestrator C3 `inventario_pipeline`). SEMPRE --dry-run+confirmacao. Ver `app/odoo/estoque/CLAUDE.md` e `ROADMAP_SKILLS.md` |
| `analista-performance-logistica` | KPIs entrega, ranking transportadoras, atrasos (read-only) |
| `gestor-motos-assai` | Pipeline B2B Q.P.A. Sendas/Assaí (estoque, recibo, separação, NF) |

### Confiabilidade de Output (OBRIGATORIO)

> Ref completa: `.claude/references/SUBAGENT_RELIABILITY.md`
> **Manual para criar/editar subagents**: `.claude/references/AGENT_DESIGN_GUIDE.md`
> **Blocos reusaveis** (pre-mortem, self-critique, output format): `.claude/references/AGENT_TEMPLATES.md`
> **Boilerplate Odoo** (REGRA ZERO, scripts, conexao): `.claude/references/odoo/AGENT_BOILERPLATE.md`
> **Avaliacao offline** (golden dataset): `.claude/evals/subagents/README.md`

Subagentes retornam resumo compactado (10:1 a 50:1). **Nao existe validacao automatica.**

**Ao spawnar subagente via Task tool**:
1. Adicionar ao prompt: "Escreva findings detalhados em `/tmp/subagent-findings/`"
2. Apos receber output: verificar `/tmp/subagent-findings/` para dados criticos
3. Para pesquisa: preferir subagentes read-only (Explore, Plan)
4. Para implementacao: REVISAR todos os arquivos tocados

**Sinais de alerta**: output sem citacao de fontes, dados sem nuances, ausencia de "nao encontrado"
