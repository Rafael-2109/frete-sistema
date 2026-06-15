<!-- doc:meta
tipo: state
camada: L3
sot_de: estado vivo + guia de retomada da limpeza de deprecados (worktree worktree-limpeza-deprecados); proxima sessao = Onda C restante + Onda E
hub: docs/superpowers/plans/INDEX.md
superseded_by: —
atualizado: 2026-06-15
-->
# Handoff — Limpeza de deprecados: Onda C restante + Onda E (proxima sessao)

> **Papel:** estado vivo + guia de retomada. Design completo: `docs/superpowers/specs/2026-06-15-limpeza-deprecados-design.md`.

## Atualizado

2026-06-15

## Estado atual

Worktree **`worktree-limpeza-deprecados`** em `.claude/worktrees/limpeza-deprecados/`, base `origin/main` (`ea1532d45`). **6 commits, lint verde:**

| commit | conteudo |
|--------|----------|
| `93b279499` | spec umbrella (6 ondas) + Apendice A (inventario verificado Onda C) |
| `ec5879cd3` | **Onda A** — 20 scripts one-off/debug/POC/PDF -> `_deprecated/` |
| `1daf96999` | **Onda B** — 6 utils mortos -> `app/utils/_deprecated/` + `csrf_helper` enxugado |
| `1d7d3bb4f` | **Onda D** — 3 AUDITORIA historicos -> `.claude/_deprecated/` + header stale corrigido |
| `631346ae4` | **Onda C (parcial)** — report de curadoria README -> text_to_SQL |
| `3537d26c2` | **Onda C (parcial)** — overlay `despesas_extras` + README_MAPEAMENTO arquivado |

SOT design: `docs/superpowers/specs/2026-06-15-limpeza-deprecados-design.md`. Curadoria text_to_SQL: `docs/superpowers/specs/2026-06-15-curadoria-semantica-text2sql.md`. Arvore de manutencao (`manutencao/semanal-2026-06-15`) intacta (so os G9 do Rafael); o cron semanal estava ativo durante a execucao — por isso worktree isolado.

**Guard de re-grep "na hora" pagou** (manter o habito): preservou `configurar_sessao_atacadao.py` e `importar_historico_odoo.py` (vivos), adiou `ml_models`/`app/database`; o lint D3 pegou drift (`peso_total`->`peso`); o check de `catalog.json` descartou overlays para `usuarios`/`relatorio_faturamento_importado` (bloqueadas).

## Pendencias

### PROXIMA SESSAO (escopo definido pelo Rafael)

1. **Onda C restante (~58 docs da raiz)** — protocolo de 4 perguntas. Disposicoes JA verificadas no **Apendice A** do spec design (22 ARQUIVAR / 17 ATUALIZAR / 19 REORGANIZAR). REGRA CRITICA: **re-grep "na hora" antes de cada move** (o Apendice A pode ter drift/erro como tiveram os recons). Placements: docs motochefe -> `app/motochefe/documentacao/` (ja existe); reference-vivos -> `docs/<tema>/` + `doc:meta` + registro em `docs/INDEX.md`; ATUALIZAR = mover+`doc:meta`+indexar + nota `trechos a reconciliar`. **Preservar:** `CARD_SEPARACAO.md`, `REGRAS_NEGOCIO.md` (citados em CLAUDE.md).
2. **Onda E (agregar organizacao)** — criar `.claude/references/PROGRESSIVE_DISCLOSURE_PATTERN.md` (reference/L2; 3 padroes: root+subdir CLAUDE.md, arvore de fluxos L3, memoria narrativa) + secoes "Module -> CLAUDE.md" e "Modulos silenciosos mas criticos" (`embeddings`/`permissions`/`resolvedores`/`supply_chain` — JAMAIS remover) em `.claude/references/INDEX.md`. Aditivo; `.claude/references/` e zona ativa (PAD-CTX) -> editar aditivamente, coordenar.

### DEFERIDOS (registrar; fora da proxima sessao)

- **Cruft local nao-rastreado** (rm na arvore principal, pos-cron): `__pycache__`/`.pyc`/`flask_session`, `tests/visual/snapshots/baseline_backup_*`, `.claire/`.
- **`ml_models.py` + `ml_models_real.py`** (`app/utils`): atados ao autodiscovery do consultando-sql (NAO-TOCAR) — decidir com a janela do text_to_SQL.
- **`app/database/__init__.py`**: NAO vazio (registra tipos PostgreSQL); 0 import direto; INVESTIGAR (infra de boot, sensivel).
- **text_to_SQL follow-up** (zona ativa): 78 field descriptions via model `info={'desc'}` na fonte; `business_rules` aos overlays JA existentes (`separacao`, `embarque_itens`, `embarques`, `entregas_monitoradas`, `transportadoras`, `contatos_agendamento`, `cidades`); `faturamento_produto` para o grao-item do conhecimento de `relatorio_faturamento_importado`.
- **Onda F (anti-drift)**: stop hook anel 3 + check skill->references + `AUDIT_POLICY.md` — FUTURO (Rafael nao incluiu na proxima sessao).
- **Fora de escopo (gated v28+/v29+):** `inventario_pipeline_service`, DROP `fretes_lancados`, ramo Selenium, SHIMs `app/odoo/services/stock_*_service`.

## Como retomar

1. Entrar no worktree: `EnterWorktree path=.claude/worktrees/limpeza-deprecados` (ou cd). Rodar comandos da **RAIZ do worktree** (hooks PAD usam path relativo).
2. Confirmar: `git branch --show-current` = `worktree-limpeza-deprecados`.
3. Ler **Apendice A** do spec design (disposicoes Onda C) + este doc.
4. Guard por item: re-grep callers/refs na hora + `url_for`/`href`/blueprint/cron + checar **mapa NAO-TOCAR** (secao 3 do spec). `git mv` -> smoke `import app` + `doc_audit.py --enforce-touched` -> commit por bloco (sem `[skip render]`).
5. Conferir se a manutencao semanal ainda esta ativa na arvore principal antes de mexer em cruft local.
