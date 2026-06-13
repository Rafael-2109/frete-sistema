<!-- doc:meta
tipo: explanation
camada: L1
sot_de: —
hub: .claude/references/INDEX.md
superseded_by: —
atualizado: 2026-06-08
-->
# Sistema de Fretes — Referencia Compartilhada

> **Papel:** referencia compartilhada do projeto, lida por AMBOS os contextos (Claude Code dev + Agent SDK web) — tech stack, regras universais, indice de referencias, caminhos do sistema e subagentes.

## Contexto

Ponto de entrada do repositorio. Conteudo dev-only (Quick Start, CSS, migrations, CLAUDE.md de modulo) versionado em `.claude/references/REGRAS_DEV_LOCAL.md` (SOT); `~/.claude/CLAUDE.md` e ponteiro local do dev. Fonte de dados por superficie: agente web = `mcp__sql__consultar_sql` + skills; Claude Code dev = MCP do Render (ver `.claude/references/INFRAESTRUTURA.md`). Campos de tabela vem dos schemas JSON; antes de qualquer skill ou operacao Odoo, ler `.claude/references/ROUTING_SKILLS.md`.

**Ultima Atualizacao**: 08/06/2026

> Este CLAUDE.md e lido por AMBOS os contextos (Claude Code dev + Agent SDK web).
> Conteudo dev-only (Quick Start, CSS, migrations) versionado em `.claude/references/REGRAS_DEV_LOCAL.md`.

---

## TECH STACK

> Verificado em 13/05/2026 (local Python 3.12.3 / Node 22.17 + Render workspace `tea-d01amimuk2gs73dhlup0`).
> Versoes exatas: `requirements.txt`, `package.json`. Detalhes infra: `.claude/references/INFRAESTRUTURA.md`.

| Camada | Stack |
|--------|-------|
| **Infra (Render, Oregon)** | Web `sistema-fretes` (Pro Plus) · Worker `sistema-fretes-worker-atacadao` (Standard, RQ) · Postgres 18 `sistema-fretes-db` (Basic 4GB) · Redis 8.1 `sistema-fretes-redis` (Starter, `allkeys_lru`) |
| **Backend** | Python 3.12 · **Flask 3.1.2** · Flask-SQLAlchemy 3.1 · Flask-Login 0.6 · Flask-Migrate 4.1 · Flask-WTF 1.2 · SQLAlchemy 2.0 · Gunicorn 25 + gevent · psycopg2 + asyncpg (pool async SessionStore) · Pydantic 2.12 · FastAPI 0.129 (endpoints isolados) |
| **Workers / Async** | RQ 2.6 · Redis 7.2 (client) · APScheduler · 3 perfis de worker (light-reserved / full / general — anti-starvation) |
| **AI / Agente** | Anthropic SDK 0.109.1 · Claude Agent SDK 0.2.101 (CLI bundled 2.1.177) · MCP 1.26 · Voyage AI + pgvector (embeddings) |
| **Browser Automation** | Playwright 1.58 (Chromium — SSW, Atacadao Hodie Booking) · Selenium 4.40 (legado) |
| **Storage** | AWS S3 via boto3 1.42 — screenshots, archives sessao, artifacts, anexos devolucao |
| **Observability** | Sentry SDK 2.54 (errors + APM) · structlog · colorlog |
| **Integracoes externas** | Odoo XML-RPC (ERP CIEL IT) · Microsoft Teams Bot Framework · WhatsApp via OpenClaw (Baileys) · Pluggy Open Finance (Bradesco) |

> Linhas dev-only do stack (Frontend/Jinja2, Artifacts React, Mobile App GPS, libs Data/Files, Build/Deploy): `.claude/references/REGRAS_DEV_LOCAL.md` secao TECH STACK COMPLEMENTO.

---

## DADOS:

### OBRIGATÓRIO (por superficie)
1. **AGENTE WEB**: dados de negocio via `mcp__sql__consultar_sql` + skills (o banco da
   aplicacao JA E producao); logs/erros/status de servicos via `mcp__render__consultar_*`.
2. **CLAUDE CODE (dev)**: dados de PRODUCAO exclusivamente via MCP do Render —
   orientacoes em `.claude/references/INFRAESTRUTURA.md`. Dados locais = dados de teste.
3. **CROSS-VERIFICACAO ODOO (ambos)**: Se o usuario pedir para verificar no Odoo, seguir roteamento em `.claude/references/odoo/ROUTING_ODOO.md`. Se encontrar inconsistencias em dados locais/Render originados do Odoo, TAMBEM verificar direto no Odoo.


## REGRAS UNIVERSAIS

### SEMPRE:
1. **AMBIENTE VIRTUAL**: `source .venv/bin/activate` quando executar scripts Python (vale para AMBAS as superficies — o runtime do Render cria `.venv` na raiz)
2. **FONTE DE DADOS (dev)**: ANTES de consultar dados reais, metricas, logs ou deploys via MCP Render: LER `.claude/references/INFRAESTRUTURA.md`
3. **TIMEZONE**: ANTES de escrever qualquer codigo com datas/timestamps: LER `.claude/references/REGRAS_TIMEZONE.md`.

---

## MODELOS CRITICOS

**Campos de tabelas**: SEMPRE usar schemas auto-gerados em `.claude/skills/consultando-sql/schemas/tables/{tabela}.json`
References contem APENAS regras de negocio, NAO campos.

**ANTES de usar CarteiraPrincipal/Separacao**: LER `.claude/references/modelos/REGRAS_CARTEIRA_SEPARACAO.md`
**ANTES de usar Embarque/Faturamento/etc.**: LER `.claude/references/modelos/REGRAS_MODELOS.md`
**ANTES de executar qualquer skill ou operacao Odoo**: LER `.claude/references/ROUTING_SKILLS.md`

Gotchas rapidos:
- CarteiraPrincipal: `qtd_saldo_produto_pedido` (NAO `qtd_saldo`)
- Separacao: `qtd_saldo` (NAO `qtd_saldo_produto_pedido`)
- Separacao tem `expedicao`, `agendamento`, `protocolo` (Carteira NAO tem)

---

## INDICE DE REFERENCIAS

> **Lista COMPLETA de references** (este indice e um subconjunto quick-reference): `.claude/references/INDEX.md`
> Indice unico consultado por AMBOS os contextos.
> Entradas dev-only (CSS, Best Practices, MCP Capabilities, CLAUDE.md de modulo) estao em `.claude/references/REGRAS_DEV_LOCAL.md` (versionado) — `~/.claude/CLAUDE.md` e ponteiro local.

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
| **Contexto do Agente Web (PAD-CTX)** — ANTES de adicionar/mover conteudo em preset, system_prompt, CLAUDE.md, listing de skills, hook ou memorias | `.claude/references/ARQUITETURA_CONTEXTO_AGENTE.md` (criterios de admissao por camada + orcamento por bloco + intocaveis) |
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

### Design System (UI/CSS) — dev-only

> Tabela completa (GUIA_COMPONENTES_UI, ui_audit, lint policy, visual regression): `.claude/references/REGRAS_DEV_LOCAL.md` secao DESIGN SYSTEM.

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
| Relatorios Fiscais (SPED ECD) | `app/relatorios_fiscais/routes.py`, `app/relatorios_fiscais/services/`, `app/relatorios_fiscais/manual_ecd/` — ver `app/relatorios_fiscais/CLAUDE.md` |
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
| **NAO ESTENDER (dev)** | `app/carteira/main_routes.py` — apenas dashboard `index()` (Fase 3 limpa). Novas rotas: usar `app/carteira/routes/` |

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
| `gestor-ssw` | Operacoes SSW multi-step (POP-A10, cadastros) (dev-only via Task — fora do loader web desde T2.1 2026-06-12, 0 invocacoes web/90d) |
| `auditor-financeiro` | Reconciliacao financeira, auditoria Local vs Odoo, SEM_MATCH |
| `auditor-sped-ecd` | Auditar SPED ECD gerado vs Manual Leiaute 9 + ground truth contadora (4 skills exclusivas parseando/auditando/comparando-sped) |
| `controlador-custo-frete` | Custo real frete, divergencia CTe, conta corrente transportadoras (dev-only via Task — fora do loader web desde T2.1 2026-06-12, 0 invocacoes web/90d) |
| `gestor-recebimento` | Pipeline recebimento 4 fases, DFEs bloqueados, troubleshooting |
| `gestor-devolucoes` | Devolucoes NFD, De-Para AI, descarte vs retorno (dev-only via Task — fora do loader web desde T2.1 2026-06-12, 0 invocacoes web/90d) |
| `gestor-estoque-producao` | Ruptura, estoque comprometido, producao vs programada (READ-ONLY) |
| `gestor-estoque-odoo` | Operacoes de **escrita** de estoque no Odoo + consulta AO VIVO (quants, transferencias, reservas, pickings, MOs, escrituracao entrada, faturamento saida) — SEMPRE dry-run + confirmacao. Status/versao das skills atomicas: `app/odoo/estoque/CLAUDE.md` + `ROADMAP_SKILLS.md` |
| `analista-performance-logistica` | KPIs entrega, ranking transportadoras, atrasos (read-only) |
| `gestor-motos-assai` | Pipeline B2B Q.P.A. Sendas/Assaí (estoque, recibo, separação, NF) |
| `orientador-loja` | Perguntas cross-entidade Lojas HORA (pedido+NF+recebimento+chassi) — exclusivo Agente Lojas HORA |

### Confiabilidade de Output (OBRIGATORIO)

> Ref completa: `.claude/references/SUBAGENT_RELIABILITY.md`
> Criar/editar subagents (manual, templates, boilerplate Odoo, evals — dev-only): `~/.claude/CLAUDE.md` secao REFERENCIAS DEV-ONLY (config pessoal local).

Subagentes retornam resumo compactado (10:1 a 50:1). **Nao existe validacao automatica.**

**Ao spawnar subagente via Task tool**:
1. Adicionar ao prompt: "Escreva findings detalhados em `/tmp/subagent-findings/`"
2. Apos receber output: verificar `/tmp/subagent-findings/` para dados criticos
3. Para pesquisa: preferir subagentes read-only (Explore, Plan)
4. Para implementacao: REVISAR todos os arquivos tocados

**Sinais de alerta**: output sem citacao de fontes, dados sem nuances, ausencia de "nao encontrado"
