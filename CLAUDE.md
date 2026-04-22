# Sistema de Fretes — Referencia Compartilhada

**Ultima Atualizacao**: 20/04/2026

> Este CLAUDE.md e lido por AMBOS os contextos (Claude Code dev + Agent SDK web).
> Conteudo dev-only (Quick Start, CSS, migrations) esta em `~/.claude/CLAUDE.md`.

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

---

## CAMINHOS DO SISTEMA

| Modulo | Caminhos corretos |
|--------|-------------------|
| Carteira de Pedidos | `app/carteira/routes/`, `app/carteira/services/`, `app/carteira/utils/`, `app/templates/carteira/` |
| Agente Web | `app/agente/` (Claude Agent SDK) — ver `app/agente/CLAUDE.md` |
| Financeiro | `app/financeiro/routes/`, `app/financeiro/services/`, `app/financeiro/workers/` — ver `app/financeiro/CLAUDE.md` |
| Odoo | `app/odoo/services/`, `app/odoo/utils/`, `app/odoo/jobs/` — ver `app/odoo/CLAUDE.md` |
| CarVia | `app/carvia/routes/`, `app/carvia/services/`, `app/templates/carvia/` — ver `app/carvia/CLAUDE.md` |
| Seguranca | `app/seguranca/routes/`, `app/seguranca/services/`, `app/templates/seguranca/` — ver `app/seguranca/CLAUDE.md` |
| Fretes | `app/fretes/routes.py`, `app/fretes/services/`, `app/templates/fretes/` |
| Recebimento | `app/recebimento/routes/`, `app/recebimento/services/`, `app/recebimento/workers/` |
| Devolucao | `app/devolucao/routes/`, `app/devolucao/services/` — ver `app/devolucao/CLAUDE.md` (dev) ou `app/devolucao/README.md` (narrativa) |
| Pallet | `app/pallet/routes/`, `app/pallet/services/`, `app/templates/pallet/` |
| Producao | `app/producao/routes.py`, `app/producao/models.py` |
| Pedidos | `app/pedidos/routes/`, `app/pedidos/services/`, `app/pedidos/workers/` |
| **OBSOLETO** | `app/carteira/main_routes.py` — NAO usar |

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
| `gestor-estoque-producao` | Ruptura, estoque comprometido, producao vs programada |
| `analista-performance-logistica` | KPIs entrega, ranking transportadoras, atrasos (read-only) |

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
