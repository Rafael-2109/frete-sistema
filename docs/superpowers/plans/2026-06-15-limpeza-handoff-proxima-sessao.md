<!-- doc:meta
tipo: state
camada: L3
sot_de: estado da limpeza de deprecados (worktree worktree-limpeza-deprecados); Ondas A-E concluidas, restam DEFERIDOS + Onda F
hub: docs/superpowers/plans/INDEX.md
superseded_by: —
atualizado: 2026-06-15
-->
# Handoff — Limpeza de deprecados: estado (Ondas A-E concluidas)

> **Papel:** estado vivo + guia de retomada. Design completo: `docs/superpowers/specs/2026-06-15-limpeza-deprecados-design.md`.

## Atualizado

2026-06-15

## Estado atual

Worktree **`worktree-limpeza-deprecados`** em `.claude/worktrees/limpeza-deprecados/`, base `origin/main` (`ea1532d45`). **Ondas A, B, C, D, E concluidas; lint `--strict` verde** (os 5 blocks remanescentes sao pre-existentes em zonas nao-tocar: `docs/industrializacao-fb-lf/` x2, `.claude/references/REGRAS_OUTPUT.md`, `.claude/skills/exportando-arquivos/SCRIPTS.md` x2).

| commit | conteudo |
|--------|----------|
| `93b279499` | spec umbrella (6 ondas) + Apendice A (inventario verificado Onda C) |
| `ec5879cd3` | **Onda A** — 20 scripts one-off/debug/POC/PDF -> `_deprecated/` |
| `1daf96999` | **Onda B** — 6 utils mortos -> `app/utils/_deprecated/` + `csrf_helper` enxugado |
| `1d7d3bb4f` | **Onda D** — 3 AUDITORIA historicos -> `.claude/_deprecated/` + header stale corrigido |
| `631346ae4` | **Onda C (parcial)** — report de curadoria README -> text_to_SQL |
| `3537d26c2` | **Onda C (parcial)** — overlay `despesas_extras` + README_MAPEAMENTO arquivado |
| `fd292d1a4` | **Onda C** — 23 docs one-shot da raiz -> `docs/_deprecated/` (re-verificacao adversarial, 0 falso-mortos) |
| `da0a1a393` | **Onda C** — 35 docs de modulo reorganizados+atualizados -> `docs/<tema>/` + `docs/INDEX.md` |
| `9acad052a` | **Onda E** — `PROGRESSIVE_DISCLOSURE_PATTERN.md` + secoes Module->CLAUDE.md e silenciosos-criticos no INDEX |

Onda C (gerenciados) aplicada apos **re-verificacao adversarial** de 58 docs (1 agente read-only por doc: re-grep na hora + Q3 contra o codigo) -> 0 falso-mortos / 0 nao-tocar / 0 conflitos; os 20 AJUSTAR foram "diretorio-novo" + reconciliacoes refinadas (inclusive drift do proprio Apendice A: nome de funcao errado, Fases 4/5/6 Motochefe ja implementadas). Raiz reduzida aos 4 preservados (`CARD_SEPARACAO.md`, `CLAUDE.md`, `README.md`, `REGRAS_NEGOCIO.md`). **NAO pushado / NAO mergeado.**

## Pendencias

### Concluido nesta sessao (2026-06-15)
- **Onda C restante** (58 docs raiz): 23 ARQUIVADOS, 17 ATUALIZADOS, 18 REORGANIZADOS (PROGRESS.md reclassificado REORGANIZAR->ARQUIVAR). doc:meta + C8 bidirecional em `docs/INDEX.md`.
- **Onda E**: `PROGRESSIVE_DISCLOSURE_PATTERN.md` (reference/L2) + 2 secoes no `.claude/references/INDEX.md`. Bidirecionalidade dos 3 hubs ja estava OK (0 C8).

### Proxima sessao / DEFERIDOS
- **Push/merge**: branch tem 3 commits novos de limpeza (`fd292d1a4`, `da0a1a393`, `9acad052a`) sobre os 6 anteriores; decidir merge p/ main.
- **Cruft local nao-rastreado** (rm na arvore principal, pos-cron): `__pycache__`/`.pyc`/`flask_session`, `tests/visual/snapshots/baseline_backup_*`, `.claire/`.
- **`ml_models.py` + `ml_models_real.py`** (`app/utils`): atados ao autodiscovery do consultando-sql (NAO-TOCAR) — decidir com a janela do text_to_SQL.
- **`app/database/__init__.py`**: nao vazio (registra tipos PostgreSQL); 0 import direto; INVESTIGAR (infra de boot).
- **text_to_SQL follow-up** (zona ativa): 78 field descriptions + `business_rules` aos overlays existentes.
- **Onda F (anti-drift)**: stop hook anel 3 + check skill->references + `AUDIT_POLICY.md` — FUTURO.
- **Gotcha hooks PAD (registrar/corrigir)**: `pad_creation_gate.py`, `pad_sot_modulo.py` e `lembrar-regenerar-schemas.py` sao invocados com path RELATIVO e falham quando o cwd e `/tmp` (subagentes de workflow e Edit/Write tool nesta sessao ficaram pinados em `/tmp`). Workaround usado: editar `.md` via Bash/Python da raiz + validar com `doc_audit --strict`. Corrigir os hooks p/ path absoluto (`$CLAUDE_PROJECT_DIR`) eliminaria a friccao.
- **Fora de escopo (gated v28+/v29+):** `inventario_pipeline_service`, DROP `fretes_lancados`, ramo Selenium, SHIMs `app/odoo/services/stock_*_service`.

## Como retomar

1. Entrar no worktree; confirmar `git branch --show-current` = `worktree-limpeza-deprecados`.
2. Rodar comandos da RAIZ do worktree (hooks PAD usam path relativo).
3. Validar docs: `python3 scripts/audits/doc_audit.py --strict --skip-dup` (esperado: 5 blocks pre-existentes em zonas nao-tocar).
4. Decidir push/merge dos 3 commits de limpeza antes de iniciar Onda F.
