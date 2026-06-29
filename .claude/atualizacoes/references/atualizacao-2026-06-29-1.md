# Atualizacao References — 2026-06-29-1

**Data**: 2026-06-29
**Grupos revisados**: P0 (27 root), P1 (11 modelos+negocio), P2 (9 odoo) em profundidade; P3-P4 (design/linx/ssw) scan rapido
**Arquivos de reference modificados**: 5 (+ 5 docs `docs/superpowers/` no Passo 0 C8)

## Resumo

Revisao completa P0-P2 (47 arquivos) + Passo 0 C8 global. **C8 reduzido de 7 orfaos -> 0** (todos em `docs/superpowers/`, fora do escopo references mas C8 e gate global). 5 references corrigidas: drift de contagem de skills 57->59 (STUDY + INDEX, +`reclassificando-amls-odoo` e `consultando-cliente-odoo` desde a auditoria de 2026-06-22), 2 cross-refs ambiguas em odoo/ (ROUTING_ODOO + GOTCHAS) e 1 data dessincronizada (INFRAESTRUTURA). **Versoes SDK conferem** (claude-agent-sdk 0.2.101 / CLI 2.1.177 / anthropic 0.109.1 / mcp >=1.26.0,<2.0.0 — sem bump desde 2026-06-13). Gotchas criticos de modelo TODOS conferem com codigo. Zero caminhos `app/*` quebrados em P0-P2.

## Passo 0 — C8 (alcancabilidade global)

7 findings iniciais, todos em `docs/superpowers/` (plans/specs datados de 2026-06-24 a 2026-06-26 — triados VIVOS via `git log`). Resolvidos:

| Arquivo | Problema C8 | Correcao |
|---------|-------------|----------|
| `plans/2026-06-25-relatorio-estoque-semanal.md` | orfao (sem doc:meta + nao listado) | + doc:meta (how-to) + ponteiro em `plans/INDEX.md` + `Papel`/`Indice` (C5/C6) |
| `plans/2026-06-26-carvia-cotacao-publica.md` | hub nao lista de volta | + ponteiro em `plans/INDEX.md` |
| `specs/2026-06-24-validador-titulos-bancos-design.md` | orfao (sem doc:meta) | + doc:meta (explanation) + ponteiro em `specs/INDEX.md` + `Papel`/`Contexto`/`Indice` |
| `specs/2026-06-25-relatorio-estoque-semanal-design.md` | orfao (sem doc:meta) | + doc:meta (explanation) + ponteiro em `specs/INDEX.md` + `Papel`/`Contexto`/`Indice` |
| `specs/2026-06-26-carvia-cotacao-publica-design.md` | hub nao lista de volta | + ponteiro em `specs/INDEX.md` |

Nota: adicionar doc:meta aos 3 orfaos "nus" os tornou docs gerenciados, ativando C5 (secoes obrigatorias) e C6 (TOC) que antes ficavam ocultos. Corrigidos no mesmo turno para `> **Papel:**` + `## Contexto` (explanation) + `## Indice`. **C8 = 0 e block = 0 nesses arquivos apos as edicoes.**

## Alteracoes por Grupo

### Root (P0)
- `STUDY_PROMPT_ENGINEERING_2026.md:89` — contagem de skills **57 -> 59** (stale desde 2026-06-25; ROUTING_SKILLS ja estava em 59).
- `INDEX.md:13` — body inventario **57 -> 59** (+`reclassificando-amls-odoo` adicionada ao mapeamento Skill->References; `consultando-cliente-odoo` ja estava); frontmatter `atualizado:` **2026-06-08 -> 2026-06-29** (estava dessincronizado do body).
- `INFRAESTRUTURA.md:28` — `**Ultima Atualizacao**` body **22/04/2026 -> 02/06/2026** (sincroniza com frontmatter `atualizado: 2026-06-02`; capacity baseline 22/04 e conteudo, mantido como nota).

### odoo/ (P2)
- `odoo/ROUTING_ODOO.md:33` — cross-ref ambigua `ROUTING_SKILLS.md` -> caminho explicito `.claude/references/ROUTING_SKILLS.md` (nao existe ROUTING_SKILLS local em odoo/).
- `odoo/GOTCHAS.md:17` — cross-ref ambigua `ROADMAP_SKILLS.md` (existe em 3 locais) -> caminho explicito `app/odoo/estoque/ROADMAP_SKILLS.md` (mesmo dir do `CLAUDE.md §8` citado na linha).

### modelos/ + negocio/ (P1)
- Sem alteracoes. Gotchas criticos verificados contra codigo (TODOS conferem):
  - CarteiraPrincipal usa `qtd_saldo_produto_pedido` (`app/carteira/models.py:47`); Separacao usa `qtd_saldo` (`app/separacao/models.py:22`).
  - Separacao tem `expedicao`/`agendamento`/`protocolo` (linhas 31/32/34); Carteira nao.
  - `local_cd`: VICTORIO_MARCHEZINE (VM) / TENENTE_MARQUES (TM), default VM (`app/utils/local_cd.py`).
  - **Falso-positivo descartado**: `REGRAS_MODELOS.md:147` "FaturamentoProduto usa `cnpj_cliente`" — CONFIRMADO correto (`app/faturamento/models.py:47` + schema json). Sub-agente sugeriu revisar; verificado e OK.

### P3-P4 (scan rapido)
- `design/` (2 files: GUIA_COMPONENTES_UI, MAPEAMENTO_CORES), `linx/INTEGRACOES.md`, `ssw/` (319 .md) — sem problemas criticos detectados no scan.

## Verificacoes que conferem (sem alteracao)
- Versoes vs requirements.txt: anthropic 0.109.1, claude-agent-sdk 0.2.101 (CLI 2.1.177), mcp >=1.26.0,<2.0.0, Flask 3.1.2, SQLAlchemy 2.0.46, pydantic 2.12.5, fastapi 0.129.0, playwright 1.58.0, selenium 4.40.0, boto3 1.42.50, sentry-sdk 2.54.0, rq 2.6.1, redis 7.2.0, gunicorn 25.1.0 — TODAS batem.
- 16 subagents (.claude/agents/) e 59 skills invocaveis (58 SKILL.md + consultando-sql DATA-only) — reconciliados.
- BEST_PRACTICES_2026, MCP_CAPABILITIES_2026, ROUTING_SKILLS, SUBAGENT_RELIABILITY, PADROES_BACKEND, ARQUITETURA_CONTEXTO_AGENTE, OBSERVABILIDADE_AGENTE: OK (todos os caminhos `app/*` citados existem).
- IDs fixos Odoo (FB/SC/CD/LF), pipeline recebimento 4 fases, tolerancias: OK.

## Itens para Revisao Manual / Carry-forward
- **STUDY_PROMPT_ENGINEERING_2026_QUALITY_REVIEW.md** (P0): doc e snapshot historico de 2026-04-12 (audita system_prompt v4.2.0->v4.3.0; "12 agents"). System_prompt real hoje = **v4.5.0**, 16 subagents. NAO corrigido — e doc point-in-time por design; revisao trimestral STUDY agendada 2026-07.
- **MANUAL_CLAUDE_MD.md** (P0): header "Versao 1.0 | Data 14/02/2026". Conceitualmente valido; data e versionamento do doc, nao drift factual.
- **IDS_FIXOS product_tmpl_id=34** (P2): pendencia historica recorrente — validacao requer MCP Odoo ao vivo (read-only, fora do alcance desta auditoria de docs).
- **6 block findings pre-existentes FORA do escopo references** (nao corrigidos — outros donos de dominio): `.claude/skills/baixando-credores-lote-odoo/DESIGN.md` (C6 TOC), `.claude/skills/exportando-arquivos/SCRIPTS.md` (D4 'varias'), `.claude/skills/gerindo-expedicao/SCRIPTS.md:289` (D3 `Separacao.atualizar_cotacao` nao existe no schema), `app/agente/services/CLAUDE.md` (C6 TOC), `app/odoo/estoque/CLAUDE.md` (C1 doc:meta ausente), `docs/roteirizacao/ESTADO.md` (C6 TOC).
