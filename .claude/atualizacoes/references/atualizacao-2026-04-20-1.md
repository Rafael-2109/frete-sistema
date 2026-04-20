# Atualizacao References 2026-04-20-1

**Data**: 2026-04-20 (correcoes aplicadas em sessao subsequente no mesmo dia)
**Escopo**: Auditoria completa de `.claude/references/` (30 arquivos)
**Status**: OK — 6/7 divergencias corrigidas; 1 pendente (IDS_FIXOS `product_tmpl_id ~34~` requer MCP Odoo)

> Relatorio originalmente escrito em `/tmp/manutencao-2026-04-20/` por bloqueio de sensitive file; movido e atualizado em `.claude/atualizacoes/references/` apos revisao humana das correcoes.

---

## Resumo

~30 arquivos revisados (P0 raiz, P1 modelos/+negocio/, P2 odoo/, P3 design/+linx/+ssw/ scan rapido). Identificadas 5 divergencias factuais (4 P0, 1 P3). Nenhum caminho quebrado. Implementacao (listeners Separacao, IDs Odoo, S3 callsites) confere com o que esta documentado nos arquivos revisados.

---

## Divergencias Encontradas

### P0 — Raiz

1. **`BEST_PRACTICES_2026.md`**
   - Header: "Ultima Atualizacao: 23/03/2026" — desatualizado
   - Versao documentada: `claude-agent-sdk==0.1.55`
   - Versao real em `requirements.txt`: `claude-agent-sdk==0.1.63` (CLI 2.1.114)
   - Diff real relevante: 0.1.60 adicionou `list_subagents()`, 0.1.62 adicionou parametro `skills=`, 0.1.63 e a atual

2. **`MCP_CAPABILITIES_2026.md`**
   - Header: "Ultima Atualizacao: 2026-03-23" — desatualizado
   - Versao documentada: `claude-agent-sdk 0.1.55`
   - Versao real em `requirements.txt`: `0.1.63`
   - Spec MCP documentada (2025-11-25) continua correta

3. **`MEMORY_PROTOCOL.md`**
   - Referencia: `app/agente/services/memory_injection.py:157` para `_calculate_category_decay`
   - Real: funcao esta na linha **173** (linha 157 nao e mais o decorator/inicio dessa funcao apos ultimas edicoes)

4. **`ROUTING_SKILLS.md`**
   - Declara "31 total" skills
   - Real: **25 skills** em `.claude/skills/` (acessando-ssw, conciliando-odoo-po, conciliando-transferencias-internas, consultando-sentry, consultando-sql, cotando-frete, descobrindo-odoo-estrutura, diagnosticando-banco, executando-odoo-financeiro, exportando-arquivos, gerando-baseline-conciliacao, gerindo-agente, gerindo-carvia, gerindo-expedicao, lendo-arquivos, lendo-documentos, monitorando-entregas, operando-portal-atacadao, operando-ssw, rastreando-odoo, razao-geral-odoo, recebimento-fisico-odoo, resolvendo-entidades, validacao-nf-po, visao-produto)

### P1 — modelos/ + negocio/

Sem divergencias criticas identificadas. Verificado:
- `modelos/REGRAS_CARTEIRA_SEPARACAO.md` — linhas dos listeners (208, 244, 293, 326) em `app/separacao/models.py` **conferem**
- `modelos/REGRAS_MODELOS.md` — prioridades de status, listener embarque batem com codigo
- Campos documentados (CarteiraPrincipal sem `separacao_lote_id`/`expedicao`/`agendamento`; Separacao com `qtd_saldo` nao `qtd_saldo_produto_pedido`) confirmados nos schemas JSON

### P2 — odoo/

Sem divergencias criticas identificadas. Verificado:
- IDs fixos (companies FB/SC/CD/LF, picking types, journals) — batem com `.claude/references/odoo/IDS_FIXOS.md`
- Modelos CIEL IT (`l10n_br_ciel_it_account.*`) referenciados corretamente
- Scripts/services citados em `GOTCHAS.md` **existem** nos caminhos indicados

6. **`odoo/IDS_FIXOS.md`** (menor — flag aberto ha 2+ meses)
   - Marcador `product_tmpl_id ~34~ VERIFICAR` aberto desde 31/Jan/2026
   - Recomendacao: verificar ID real via MCP Odoo em proxima sessao, ou remover flag

### P0 extra — INDEX.md (descoberto na revisao de cross-refs)

7. **`INDEX.md`** — sem entradas para `AGENT_DESIGN_GUIDE.md` e `AGENT_TEMPLATES.md`
   - Ambos referenciados no `CLAUDE.md` raiz secao SUBAGENTES
   - Ausentes da tabela "Consulta Rapida" em INDEX.md
   - Proposto adicionar:
     - `| **Manual para criar/editar subagents** | [AGENT_DESIGN_GUIDE.md](AGENT_DESIGN_GUIDE.md) |`
     - `| **Blocos reusaveis (pre-mortem, self-critique, output format)** | [AGENT_TEMPLATES.md](AGENT_TEMPLATES.md) |`

### P3 — design/

5. **`design/MAPEAMENTO_CORES.md`**
   - Referencia `bootstrap-overrides.css` na raiz de `app/static/css/`
   - Real: arquivo esta em `app/static/css/base/_bootstrap-overrides.css` (dentro do sistema de layers)
   - Arquivo antigo `bootstrap-theme-override.css` foi **removido** (confirmado via `app/templates/base.html:10` que nao o importa mais)

### P3 — linx/, ssw/

Scan rapido — sem anomalias evidentes.

---

## Correcoes Aplicadas (2026-04-20 — sessao subsequente)

| # | Arquivo | Acao | Status |
|---|---------|------|--------|
| 1 | `BEST_PRACTICES_2026.md` | Header 23/03 -> 20/04 + SDK 0.1.55 -> 0.1.63 (nota 0.1.60/0.1.62/0.1.63) | APLICADA |
| 2 | `MCP_CAPABILITIES_2026.md` | Header 2026-03-23 -> 2026-04-20 + SDK 0.1.55 -> 0.1.63 (idem) | APLICADA |
| 3 | `MEMORY_PROTOCOL.md` | Linha 157 -> 173 + path completo `app/agente/sdk/memory_injection.py` | APLICADA |
| 4 | `ROUTING_SKILLS.md` | Contagem 31 -> 25; inventario reescrito; removidas 6 skills inexistentes | APLICADA |
| 5 | `design/MAPEAMENTO_CORES.md` | Path `bootstrap-overrides.css` -> `base/_bootstrap-overrides.css` (2 ocorrencias) | APLICADA |
| 6 | `odoo/IDS_FIXOS.md` | Flag `product_tmpl_id ~34~ VERIFICAR` | **PENDENTE** (requer MCP Odoo) |
| 7 | `INDEX.md` | +2 entradas (AGENT_DESIGN_GUIDE, AGENT_TEMPLATES) + header 12/04 -> 20/04 | APLICADA |

### Pendencia #6 (product_tmpl_id)
Flag `~34~ VERIFICAR` aberto desde 31/Jan/2026 em `odoo/IDS_FIXOS.md`. Requer consulta MCP Odoo ao modelo `product.product` para confirmar `product_tmpl_id` real do produto vinculado. Nao aplicado nesta sessao por falta de evidencia concreta (regra "zero invencao" do precision-engineer).

---

## Historico

- Auditoria 2026-04-06 encontrou 6 divergencias, nao corrigidas (mesmo motivo sensitive file).
- Auditoria 2026-04-20 encontrou 7 divergencias, **6 corrigidas** apos revisao humana liberar sensitive files, 1 pendente (MCP Odoo).

Nenhum caminho quebrado critico. Sem deletar ou renomear arquivos.
