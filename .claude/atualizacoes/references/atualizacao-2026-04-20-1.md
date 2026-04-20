# Atualizacao References 2026-04-20-1 (COPIA /tmp — destino .claude/ bloqueado)

**Data**: 2026-04-20
**Escopo**: Auditoria completa de `.claude/references/` (30 arquivos)
**Status**: PARCIAL — divergencias documentadas, correcoes NAO aplicadas (permissao bloqueada em arquivos sensiveis sob `.claude/`, incluindo este proprio relatorio em seu destino final)

> Destino original: `.claude/atualizacoes/references/atualizacao-2026-04-20-1.md` — WRITE bloqueado como "sensitive file". Relatorio escrito em `/tmp/manutencao-2026-04-20/` para registro; mover manualmente para `.claude/atualizacoes/references/` quando autorizado.

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

## Divergencias NAO Corrigidas — Motivo

Tentativa de `Edit`/`Write` em arquivos `.claude/references/*.md` e no proprio destino do relatorio foi bloqueada com:

> Claude requested permissions to edit ... which is a sensitive file.

Mesmo comportamento da auditoria 2026-04-06 (6 divergencias encontradas, nao corrigidas — permissao). Convencao: **documentar divergencias sem aplicar edits**, liberando para revisao humana.

---

## Recomendacoes para proxima sessao (com permissao)

1. Atualizar `claude-agent-sdk` 0.1.55 -> 0.1.63 em `BEST_PRACTICES_2026.md` e `MCP_CAPABILITIES_2026.md` + carimbar data 2026-04-20. Nota: instalado em `.venv` e 0.1.60 (rodar `pip install -U -r requirements.txt` para alinhar)
2. Atualizar referencia de linha em `MEMORY_PROTOCOL.md` (157 -> 173) ou remover numero de linha para reduzir drift
3. Atualizar contagem de skills em `ROUTING_SKILLS.md` (31 -> 24 invocaveis + 1 data folder) e reescrever o inventario das linhas 132-154 (remove `frontend-design`, `skill-creator`, `ralph-wiggum`, `prd-generator`, `resolvendo-problemas`, `integracao-odoo` que nao existem em `.claude/skills/`)
4. Atualizar caminho CSS em `design/MAPEAMENTO_CORES.md` (remover referencia a `bootstrap-theme-override.css` e apontar para `base/_bootstrap-overrides.css`)
5. Adicionar 2 entradas em `INDEX.md` Consulta Rapida para `AGENT_DESIGN_GUIDE.md` e `AGENT_TEMPLATES.md`
6. Verificar `product_tmpl_id ~34~` em `odoo/IDS_FIXOS.md` via MCP Odoo ou remover flag (aberto desde 31/Jan/2026)
7. Mover este relatorio de `/tmp/manutencao-2026-04-20/` para `.claude/atualizacoes/references/` e adicionar entrada em `historico.md`

Nenhum caminho quebrado critico. Sem deletar ou renomear arquivos.
