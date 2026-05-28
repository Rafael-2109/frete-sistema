"""ALIAS COMPAT — `faturamento_pipeline` renomeado para `inventario_pipeline` em v27+ S3.

Re-exporta TODOS os simbolos publicos do modulo novo
`app/odoo/estoque/orchestrators/inventario_pipeline.py`. Preserva 100%
dos imports externos historicos (8+ callers em testes + docstrings +
scripts ad-hoc) sem quebra retrocompatibilidade.

CONSTITUICAO §6 (catalogo atualizado v27+):
  - Skill 8 ATOMICA L2 = `app/odoo/estoque/scripts/faturamento.py`
    (5 atomos sobre account.move — v24+ AP6 refator).
  - Orchestrator C3 LEGACY = `inventario_pipeline.py` (renomeado de
    `faturamento_pipeline.py` em v27+ S3). Pipeline A-F + recovery +
    opt-in `--usar-skill8-atomica-v25` + opt-in `--usar-fluxo-l3-v19`.

CR-v27-1: este STUB EMITE `DeprecationWarning` em runtime quando
importado, alertando callers que `faturamento_pipeline` virou alias
para `inventario_pipeline`. Migracao gradual dos callers para o nome
novo planejada v28+ (apos canary REAL PROD do opt-in v25+ S1 validar
paridade vs legacy).

FAQ:
  Q: Por que stub em vez de remover diretamente?
  A: 8+ callers (testes + docstrings + scripts ad-hoc + memorias) usam
     `app.odoo.estoque.orchestrators.faturamento_pipeline` como path.
     Stub preserva imports = zero risco regressao. Apos canary v25+ S1
     validar opt-in, migrar callers para `inventario_pipeline` direto.

  Q: Quando remover este stub?
  A: v28+ apos:
     - Canary REAL PROD do opt-in `--usar-skill8-atomica-v25` validado.
     - grep -r `faturamento_pipeline` retorna SO docstrings (sem
       imports Python ativos).
     - PROTECAO_PROXIMA_SESSAO.md atualiza N32 "alias removido em v28+".

Spec: app/odoo/estoque/PROMPT_PROXIMA_SESSAO.md v27+ §3 S3
Refs:
  - CLAUDE.md §6 Tabela 3 (Orchestrators C3)
  - .claude/skills/faturando-odoo/SKILL.md (fachada — apontar para
    inventario_pipeline em v27+ S3)
"""
import warnings as _warnings

_warnings.warn(
    "`app.odoo.estoque.orchestrators.faturamento_pipeline` foi "
    "renomeado para `inventario_pipeline` em v27+ S3 (constituicao "
    "§6 catalogo: Skill 8 ATOMICA L2 = scripts/faturamento.py, "
    "Orchestrator C3 = orchestrators/inventario_pipeline.py). "
    "Atualize seu import para "
    "`from app.odoo.estoque.orchestrators.inventario_pipeline import ...` "
    "— este stub sera removido em v28+ apos canary REAL PROD do "
    "opt-in --usar-skill8-atomica-v25 validar paridade.",
    DeprecationWarning,
    stacklevel=2,
)

# Re-export TODOS simbolos publicos. NAO usa `*` porque modulo expoe
# constants, helpers, classes — preserva nomes esperados pelos callers.
from app.odoo.estoque.orchestrators.inventario_pipeline import *  # noqa: F401,F403,E402

# Re-export explicito dos simbolos NAO publicos (prefixo _) usados
# pelos testes em patch (mocks). Pyright nao re-exporta `_*` via `*`.
from app.odoo.estoque.orchestrators.inventario_pipeline import (  # noqa: F401,E402
    _agrupar_em_chunks,
    _agrupar_por_direcao,
    _carregar_ajustes,
    _commit_resilient,
    _pre_flight_via_subskill_c5,
    _project_root,
    _registrar_auditoria,
    _resolver_picking_metadata,
    main as _main,  # entry-point CLI para `python -m faturamento_pipeline`
)


if __name__ == '__main__':
    # Preserva entry-point CLI legacy `python -m
    # app.odoo.estoque.orchestrators.faturamento_pipeline ...`
    # Migracao para `python -m ...inventario_pipeline ...` recomendada.
    import sys as _sys
    _sys.exit(_main())
