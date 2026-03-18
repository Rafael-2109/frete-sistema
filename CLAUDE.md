# Sistema de Fretes — Referencia Compartilhada

**Ultima Atualizacao**: 17/03/2026

> Este CLAUDE.md e lido por AMBOS os contextos (Claude Code dev + Agent SDK web).
> Conteudo dev-only (Quick Start, CSS, migrations) esta em `~/.claude/CLAUDE.md`.

---

## DADOS:

### OBRIGATÓRIO
1. **FONTE PARA CONSULTA**: Utilize exclusivamente o MCP do Render, orientações em: `.claude/references/INFRAESTRUTURA.md`
2. **NÃO UTILIZAR**: Dados locais = Dados teste.


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
| **Fluxos de reconciliacao financeira** | `app/financeiro/FLUXOS_RECONCILIACAO.md` |
| **Timezone (convencao Brasil naive)** | `.claude/references/REGRAS_TIMEZONE.md` |
| **Routing de skills** | `.claude/references/ROUTING_SKILLS.md` |
| **Infraestrutura Render** | `.claude/references/INFRAESTRUTURA.md` |
| **Confiabilidade de subagentes** | `.claude/references/SUBAGENT_RELIABILITY.md` |
| **Manual CLAUDE.md de modulo** | `.claude/references/MANUAL_CLAUDE_MD.md` |
| **Capacidades MCP (versoes, gaps, enhanced)** | `.claude/references/MCP_CAPABILITIES_2026.md` |
| **Linx Microvix (APIs, WS, integracao)** | `.claude/references/linx/INTEGRACOES.md` |
| **CarVia (frete subcontratado)** | `app/carvia/CLAUDE.md` |
| **CarVia — Revisao de Gaps (37 gaps)** | `app/carvia/REVISAO_GAPS.md` |
| **Botoes, badges e cores (qual classe usar)** | `.claude/references/design/GUIA_COMPONENTES_UI.md` |
| **Portal Atacadao (automacao Hodie Booking)** | `.claude/skills/operando-portal-atacadao/SKILL.md` |
| **Best Practices Anthropic 2026** | `.claude/references/BEST_PRACTICES_2026.md` |
| Indice completo | `.claude/references/INDEX.md` |

Documentos adicionais:
- Card de Separacao: `CARD_SEPARACAO.md` (raiz)
- Sistema de Devolucoes: `app/devolucao/README.md`
- **SSW Sistemas (documentacao completa)**: `.claude/references/ssw/INDEX.md`

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
| Devolucao | `app/devolucao/routes/`, `app/devolucao/services/` — ver `app/devolucao/README.md` |
| Pallet | `app/pallet/routes/`, `app/pallet/services/`, `app/templates/pallet/` |
| Producao | `app/producao/routes.py`, `app/producao/models.py` |
| **OBSOLETO** | `app/carteira/main_routes.py` — NAO usar |

> Para lista completa de modulos e rotas: `.claude/references/INDEX.md`

---

## SUBAGENTES

| Agent | Quando Usar |
|-------|-------------|
| `analista-carteira` | Analise P1-P7, comunicacao PCP/Comercial |
| `especialista-odoo` | Problema cross-area Odoo |
| `raio-x-pedido` | Visao 360 do pedido |
| `desenvolvedor-integracao-odoo` | Criar/modificar integracoes Odoo |

### Confiabilidade de Output (OBRIGATORIO)

> Ref completa: `.claude/references/SUBAGENT_RELIABILITY.md`

Subagentes retornam resumo compactado (10:1 a 50:1). **Nao existe validacao automatica.**

**Ao spawnar subagente via Task tool**:
1. Adicionar ao prompt: "Escreva findings detalhados em `/tmp/subagent-findings/`"
2. Apos receber output: verificar `/tmp/subagent-findings/` para dados criticos
3. Para pesquisa: preferir subagentes read-only (Explore, Plan)
4. Para implementacao: REVISAR todos os arquivos tocados

**Sinais de alerta**: output sem citacao de fontes, dados sem nuances, ausencia de "nao encontrado"
