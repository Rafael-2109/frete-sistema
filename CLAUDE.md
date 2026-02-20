# Sistema de Fretes — Instrucoes de Projeto

**Ultima Atualizacao**: 14/02/2026

---

## REGRAS UNIVERSAIS

### SEMPRE:
1. **AMBIENTE VIRTUAL**: `source .venv/bin/activate` quando executar scripts Python
2. **NUNCA criar tela sem acesso via UI** — TODA tela DEVE ter link no menu (`app/templates/base.html`) ou em tela relacionada
3. **NUNCA mantenha lixo** — codigo substituido DEVE ser removido
4. **DADOS DE PRODUCAO**: ANTES de consultar dados reais, metricas, logs ou deploys: LER `.claude/references/INFRAESTRUTURA.md`
5. **OBRIGATORIO — TIMEZONE**: ANTES de escrever qualquer codigo com datas/timestamps: LER `.claude/references/REGRAS_TIMEZONE.md`. Hook `ban_datetime_now.py` bloqueia violacoes (exit 1).
6. **QUALIDADE > VELOCIDADE**: Sempre opte por pesquisar demais do que ser rápido mas não verificar algo importante.

### ANTES DE PROPOR NOVOS ARQUIVOS:
1. **LER** o INDICE DE REFERENCIAS abaixo
2. **VERIFICAR** se conteudo ja existe — se SIM, NAO criar novo
3. **MOSTRAR** o que cada arquivo existente contem antes de criar novo

**Se nao souber onde encontrar uma informacao**: LER `.claude/references/INDEX.md`

---

## MIGRATIONS

**SEMPRE gerar DOIS artefatos** para DDL (ALTER/CREATE/DROP):
1. `scripts/migrations/NOME.py` — Python com `create_app()` + verificacao before/after
2. `scripts/migrations/NOME.sql` — SQL idempotente para Render Shell (`IF NOT EXISTS`)

Excecao: data fixes (UPDATE/INSERT sem DDL) podem ser apenas Python.

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
| **Timezone (convencao Brasil naive)** | `.claude/references/REGRAS_TIMEZONE.md` |
| **Routing de skills** | `.claude/references/ROUTING_SKILLS.md` |
| **Infraestrutura Render** | `.claude/references/INFRAESTRUTURA.md` |
| **Confiabilidade de subagentes** | `.claude/references/SUBAGENT_RELIABILITY.md` |
| **Manual CLAUDE.md de modulo** | `.claude/references/MANUAL_CLAUDE_MD.md` |
| **Capacidades MCP (versoes, gaps, enhanced)** | `.claude/references/MCP_CAPABILITIES_2026.md` |
| Indice completo | `.claude/references/INDEX.md` |

Documentos adicionais:
- Card de Separacao: `CARD_SEPARACAO.md` (raiz)
- Sistema de Devolucoes: `app/devolucao/README.md`
- **SSW Sistemas (documentacao completa)**: `.claude/references/ssw/INDEX.md`

---

## ARQUITETURA CSS

**Sistema de layers** (`main.css`): `tokens → base → components → modules → utilities`
- `bootstrap-theme-override.css` FORA de layers (sobrescreve Bootstrap CDN)

### REGRAS CSS:
1. **NUNCA adicionar `<style>` blocks em templates** — usar CSS de modulo (`modules/_nome.css`)
2. **Badges compartilhados** (3+ modulos): `components/_badges.css` usando API `--_badge-bg/color/border`
3. **Badges de modulo**: no CSS do modulo (`_fretes.css`, `_financeiro.css`, `_manufatura.css`)
4. **Cores**: SEMPRE usar design tokens (`var(--text)`, `var(--bg-light)`, etc.) — NUNCA hex hardcoded
5. **Dark mode**: tokens adaptam automaticamente. Se precisar ajuste: `[data-bs-theme="light"]` selector

| Arquivo | Papel |
|---------|-------|
| `css/components/_badges.css` | Fonte unica para badges compartilhados |
| `css/bootstrap-theme-override.css` | Ponte Bootstrap CDN → design tokens |
| `css/tokens/_design-tokens.css` | Tokens de design (light/dark) |
| `css/main.css` | Entry point do sistema de layers |
| `css/modules/_*.css` | Estilos por modulo (fretes, financeiro, etc.) |

---

## CAMINHOS DO SISTEMA

| Modulo | Caminhos corretos |
|--------|-------------------|
| Carteira de Pedidos | `app/carteira/routes/`, `app/carteira/services/`, `app/carteira/utils/`, `app/templates/carteira/` |
| Agente Web | `app/agente/` (Claude Agent SDK) |
| **OBSOLETO** | `app/carteira/main_routes.py` — NAO usar |

---

## AGENTE LOGISTICO WEB

| Arquivo | Publico-Alvo |
|---------|--------------|
| **CLAUDE.md** | Claude Code (dev) |
| **system_prompt.md** | Agente Web (usuarios finais) |

**NAO MISTURAR**: Regras P1-P7 pertencem ao `system_prompt.md`, nao ao CLAUDE.md.

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

---

## SUBDIRECTORY CLAUDE.md (Planejados)

> **Manual**: `.claude/references/MANUAL_CLAUDE_MD.md` — template, principios, checklist e exemplo comentado

Modulos complexos terao CLAUDE.md proprio com patterns, convencoes e gotchas de desenvolvimento:
- `app/financeiro/CLAUDE.md` — P0 (38.7K LOC, 64 arquivos)
- `app/recebimento/CLAUDE.md` — P0 (27.3K LOC, 28 arquivos)
- `app/carteira/CLAUDE.md` — P1 (19K LOC, 49 arquivos)
- `app/odoo/CLAUDE.md` — P1 (16.8K LOC, 30 arquivos)
- `app/pallet/CLAUDE.md` — P2 (13.3K LOC, 27 arquivos)
- `app/agente/CLAUDE.md` — P2 (11.9K LOC, 35 arquivos)

---

## MCP — Context7

Usar para documentacao de libs externas:
```
resolve-library-id("sqlalchemy") -> query-docs("/...", "bulk insert")
```
