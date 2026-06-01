# Atualizacao CLAUDE.md — 2026-06-01-1

**Data**: 2026-06-01
**Arquivos auditados**: 9/9
**Arquivos modificados**: 9 (8 conteudo/data + raiz)

## Resumo

Auditados os 9 CLAUDE.md. Mudanca estrutural maior: o modulo `agente` cresceu
80 -> 96 arquivos (~41.9K -> ~48.9K LOC) com o blueprint/flywheel (Ondas A3/A4)
agora em main — novos arquivos em `config/`, `sdk/`, `tools/`, `workers/` e 3
services novos. Modulo `odoo` cresceu 63 -> 70 arquivos (~28.8K -> ~41.9K LOC),
puxado pelo subpacote `estoque/` (13 -> 19 arquivos / ~6.7K -> ~19.4K LOC) com as
Skills 7/8 (escrituracao + faturamento). Raiz: versao do Claude Agent SDK estava
defasada (0.1.80 -> 0.2.87). CarVia +0.3K LOC organico. Carteira, financeiro,
seguranca e teams sem variacao estrutural (datas nao alteradas — nada mudou).

## Alteracoes por Arquivo

### `CLAUDE.md` (raiz)
- [x] `Ultima Atualizacao`: 25/05/2026 -> 01/06/2026
- [x] Tech stack AI/Agente (linha 20): `Claude Agent SDK 0.1.80 (CLI 2.1.138)` ->
  `0.2.87 (CLI 2.1.150)`. Fonte: `requirements.txt` (`claude-agent-sdk==0.2.87`)
  + `app/agente/SDK_CHANGELOG.md` (CLI bundled 2.1.150)

### `app/agente/CLAUDE.md`
- [x] Header: `~41.9K | Arquivos: 80` -> `~48.9K | Arquivos: 96`; data -> 01/06/2026
- [x] `config/` 6 -> 8 arquivos: +`capability_registry.py`, +`skills_whitelist.py`
- [x] `sdk/` 17 -> 22 arquivos: +`context_enrichment.py`, +`plan_state.py`,
  +`plan_triage.py`, +`sticky_session.py`, +`verifiers.py`
- [x] `services/` 17 -> 20 arquivos: +`directive_promotion_service.py` (A4),
  +`eval_gate_service.py` (A3), +`ontology_bootstrap.py`
- [x] `tools/` 12 -> 13 arquivos: +`ontology_query_tool.py`
- [x] `workers/` 3 -> 8 arquivos: +`background_jobs.py`, +`eval_runner.py`,
  +`plan_verifier.py`, +`step_judge.py`, +`triage_shadow.py`

### `app/agente/services/CLAUDE.md`
- [x] Header: `~10.5K | 17` -> `~11.9K | 20`; data -> 2026-06-01
- [x] Estrutura: +`eval_gate_service.py` (568 LOC), +`directive_promotion_service.py`
  (498 LOC), +`ontology_bootstrap.py` (211 LOC)

### `app/carvia/CLAUDE.md`
- [x] LOC: `~66.9K` -> `~67.2K` (organico, 67245 reais); data -> 2026-06-01
- [x] Arquivos (107) e templates (109) inalterados — conferem

### `app/odoo/CLAUDE.md`
- [x] Header: `63 arquivos / ~28.8K LOC` -> `70 / ~41.9K LOC`; data -> 01/06/2026
- [x] Linha 7 (estoque): `13 arquivos / ~6.7K LOC` -> `19 / ~19.4K LOC`
- [x] Arvore estoque (linha 70): mesma correcao de contagem
- [x] Arvore `scripts/`: +`_commit_helpers.py`, +`_invoice_helpers.py`,
  +`escrituracao.py` (Skill 7), +`faturamento.py` (Skill 8),
  +`cadastro_fiscal_audit.py` (PRE-FLIGHT)
- [x] Arvore `orchestrators/`: +`inventario_pipeline.py` (renomeado de
  faturamento_pipeline v27+ S3)
- [x] `services/` "21 services" mantido (22 .py = 21 + `__init__.py`, correto)
- [x] `utils/` 12 -> 13: +`classificacao_produto.py` (decide se entrada/compra
  registra em MovimentacaoEstoque + natureza por categ_id/tipo fiscal, ~138 LOC)

## Apenas Data Atualizada (sem mudanca estrutural)
> Contagens/LOC conferidos e estaveis; somente o header `Atualizado` foi
> sincronizado para 01/06/2026 (procedimento padrao da auditoria).
- `app/carteira/CLAUDE.md` — 50 arquivos / 18.485 LOC (~18.5K) / 22 JS / 13 html: confere; data 25/05 -> 01/06
- `app/financeiro/CLAUDE.md` — 80 arquivos / 46.116 LOC (~46.1K): confere; data 25/05 -> 01/06
- `app/seguranca/CLAUDE.md` — 14 arquivos / 1.953 LOC (~2K) / 8 templates: confere; data 25/05 -> 01/06
- `app/teams/CLAUDE.md` — 4 arquivos / 2.560 LOC (~2.5K): confere; data 25/05 -> 01/06

## Verificacao de Caminhos
Todos os caminhos citados nos arquivos modificados foram confirmados como
existentes (Fontes P1-P8 do odoo, blueprint-agente/EXECUCAO.md +
PROMPT_PROXIMA_SESSAO_A4.md, SDK_CHANGELOG.md, estoque/PROTECAO + ROADMAP +
fluxos/). Nenhum caminho inexistente encontrado.

## Notas
- `app/odoo/estoque/CLAUDE.md` NAO esta no escopo dos 9 arquivos deste dominio;
  seu auto-count (na verbose header de status) nao foi auditado aqui, mas a
  referencia a ele no `app/odoo/CLAUDE.md` foi corrigida (19 arquivos / ~19.4K).
- Contagens LOC sao `find -name "*.py" -exec wc -l + | tail -1` (inclui blank/comments);
  templates HTML contados separadamente em `app/templates/{modulo}/`.
